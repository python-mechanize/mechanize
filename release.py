"""%prog RELEASE_AREA [action ...]

Perform needed actions to release mechanize, doing the work in directory
RELEASE_AREA.

If no actions are given, print the tree of actions and do nothing.

This is only intended to work on Unix (unlike mechanize itself).  Some of it
only works on Ubuntu karmic.

Warning:

 * Some ("clean*") actions do rm -rf on RELEASE_AREA or subdirectories of
RELEASE_AREA.

 * The install_deps action installs some debian packages system-wide.  The
clean action doesn't uninstall them.

 * The install_deps action downloads and installs software to RELEASE_AREA.
The clean action uninstalls (by rm -rf).
"""

# This script depends on the code from this git repository:
# git://github.com/jjlee/mechanize-build-tools.git

# TODO

#  * Keep version in one place!
#  * 0install package?
#  * test in a Windows VM

import glob
import optparse
import os
import re
import shutil
import smtplib
import subprocess
import sys
import tempfile
import time
import unittest

# Stop the test runner from reporting import failure if these modules aren't
# available or not running under Python >= 2.6.  AttributeError occurs if run
# with Python < 2.6, due to lack of collections.namedtuple
try:
    import email.mime.text

    import action_tree
    import cmd_env

    import buildtools.release as release
except (ImportError, AttributeError):
    # fake module
    class action_tree(object):
        @staticmethod
        def action_node(func):
            return func

# based on Mark Seaborn's plash build-tools (action_tree) and Cmed's in-chroot
# (cmd_env) -- which is also Mark's idea


class WrongVersionError(Exception):

    pass


class MissingVersionError(Exception):

    def __init__(self, path, release_version):
        Exception.__init__(self, path, release_version)
        self.path = path
        self.release_version = release_version

    def __str__(self):
        return ("Release version string not found in %s: should be %s" %
                (self.path, self.release_version))


class CSSValidationError(Exception):

    def __init__(self, path, details):
        Exception.__init__(self, path, details)
        self.path = path
        self.details = details

    def __str__(self):
        return ("CSS validation of %s failed:\n%s" % 
                (self.path, self.details))


def run_performance_tests(path):
    # TODO: use a better/standard test runner
    sys.path.insert(0, os.path.join(path, "test"))
    test_runner = unittest.TextTestRunner(verbosity=1)
    test_loader = unittest.defaultTestLoader
    modules = []
    for module_name in ["test_performance"]:
        module = __import__(module_name)
        for part in module_name.split('.')[1:]:
            module = getattr(module, part)
        modules.append(module)
    suite = unittest.TestSuite()
    for module in modules:
        test = test_loader.loadTestsFromModule(module)
        suite.addTest(test)
    result = test_runner.run(test)
    return result


def send_email(from_address, to_address, subject, body):
    msg = email.mime.text.MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = to_address
    # print "from_address %r" % from_address
    # print "to_address %r" % to_address
    # print "msg.as_string():\n%s" % msg.as_string()
    s = smtplib.SMTP()
    s.sendmail(from_address, [to_address], msg.as_string())
    s.quit()


def ensure_unmodified(env, path):
    # raise if working tree differs from HEAD
    release.CwdEnv(env, path).cmd(["git", "diff", "--exit-code", "HEAD"])


def add_to_path_cmd(value):
    set_path_script = """\
if [ -n "$PATH" ]
  then
    export PATH="$PATH":%(value)s
  else
    export PATH=%(value)s
fi
exec "$@"
""" % dict(value=value)
    return ["sh", "-c", set_path_script, "inline_script"]


def ensure_trailing_slash(path):
    return path.rstrip("/") + "/"


class Releaser(object):

    def __init__(self, env, git_repository_path, release_dir, mirror_path,
                 build_tools_repo_path=None, run_in_repository=False,
                 tag_name=None):
        env = release.GitPagerWrapper(env)
        self._release_dir = release_dir
        self._opt_dir = os.path.join(release_dir, "opt")
        self._bin_dir = os.path.join(self._opt_dir, "bin")
        AddToPathEnv = release.make_env_maker(add_to_path_cmd)
        self._env = AddToPathEnv(env, self._bin_dir)
        self._source_repo_path = git_repository_path
        self._in_source_repo = release.CwdEnv(self._env,
                                              self._source_repo_path)
        self._previous_version, self._release_version = \
            self._get_next_release_version()
        if tag_name is not None:
            self._release_version = release.parse_version(tag_name)
        self._source_distributions = self._get_source_distributions(
            self._release_version)
        self._clone_path = os.path.join(release_dir, "clone")
        self._in_clone = release.CwdEnv(self._env, self._clone_path)
        if run_in_repository:
            self._in_repo = self._in_source_repo
            self._repo_path = self._source_repo_path
        else:
            self._in_repo = self._in_clone
            self._repo_path = self._clone_path
        self._docs_dir = os.path.join(self._repo_path, "docs")
        self._in_docs_dir = release.CwdEnv(self._env, self._docs_dir)
        self._in_release_dir = release.CwdEnv(self._env, self._release_dir)
        self._build_tools_path = build_tools_repo_path
        if self._build_tools_path is not None:
            self._website_source_path = os.path.join(self._build_tools_path,
                                                     "website")
        self._mirror_path = mirror_path
        self._in_mirror = release.CwdEnv(self._env, self._mirror_path)
        self._easy_install_test_dir = "easy_install_test"
        self._easy_install_env = cmd_env.set_environ_vars_env(
            [("PYTHONPATH", self._easy_install_test_dir)],
            cmd_env.clean_environ_except_home_env(self._in_release_dir))
        self._css_validator_path = "css-validator"

    def _get_next_release_version(self):
        tags = release.get_cmd_stdout(self._in_source_repo,
                                      ["git", "tag", "-l"]).split()
        versions = [release.parse_version(tag) for tag in tags]
        if versions:
            most_recent = max(versions)
            return most_recent, most_recent.next_version()
        else:
            # --pretend
            return "dummy version", "dummy version"

    def _get_source_distributions(self, version):
        def dist_basename(version, format):
            return "mechanize-%s.%s" % (version, format)
        return set([dist_basename(version, "zip"),
                    dist_basename(version, "tar.gz")])

    def print_next_tag(self, log):
        print self._release_version

    def _verify_version(self, path):
        if str(self._release_version) not in \
                release.read_file_from_env(self._in_repo, path):
            raise MissingVersionError(path, self._release_version)

    def _verify_versions(self):
        for path in ["ChangeLog", "setup.py"]:
            self._verify_version(path)

    def clone(self, log):
        self._env.cmd(["git", "clone",
                       self._source_repo_path, self._clone_path])

    def checks(self, log):
        self._verify_versions()

    def _ensure_installed(self, package_name, ppa):
        release.ensure_installed(self._env,
                                 cmd_env.PrefixCmdEnv(["sudo"], self._env),
                                 package_name,
                                 ppa=ppa)

    def install_css_validator_in_release_dir(self, log):
        jar_dir = os.path.join(self._release_dir, self._css_validator_path)
        self._env.cmd(release.rm_rf_cmd(jar_dir))
        self._env.cmd(["mkdir", "-p", jar_dir])
        in_jar_dir = release.CwdEnv(self._env, jar_dir)
        in_jar_dir.cmd([
                "wget",
                "http://www.w3.org/QA/Tools/css-validator/css-validator.jar"])
        in_jar_dir.cmd(["wget",
                        "http://jigsaw.w3.org/Distrib/jigsaw_2.2.6.tar.bz2"])
        in_jar_dir.cmd(["sh", "-c", "tar xf jigsaw_*.tar.bz2"])
        in_jar_dir.cmd(["ln", "-s", "Jigsaw/classes/jigsaw.jar"])

    def install_haskell_platform_in_release_dir(self, log):
        # TODO: test
        version = "haskell-platform-2009.2.0.2"
        tarball = "%s.tar.gz" % version
        self._in_release_dir.cmd([
                "wget",
                "http://hackage.haskell.org/platform/2009.2.0.2/" + tarball])
        self._in_release_dir.cmd(["tar", "xf", tarball])
        in_src_dir = release.CwdEnv(self._env,
                                    os.path.join(self._release_dir, version))
        in_src_dir.cmd(["sh", "-c", "./configure --prefix=%s" % self._opt_dir])
        in_src_dir.cmd(["make"])
        #self._env.cmd(["mkdir", "-p", self._opt_dir])
        in_src_dir.cmd(["make", "install"])
        self._env.cmd(["cabal", "update"])
        self._env.cmd(["cabal", "upgrade", "--prefix", self._opt_dir,
                       "cabal-install"])

    def install_pandoc_in_release_dir(self, log):
        self._env.cmd(["cabal", "install", "--prefix", self._opt_dir,
                       "-fhighlighting",
                       "pandoc"])

    @action_tree.action_node
    def install_deps(self):
        dependency_actions = []
        def add_dependency(package_name, ppa=None):
            dependency_actions.append(
                (package_name.replace(".", ""),
                 lambda log: self._ensure_installed(package_name, ppa)))
        add_dependency("python2.4"),
        add_dependency("python2.5")
        add_dependency("python2.6")
        add_dependency("python-setuptools")
        # for deployment to SF and local collation of files for release
        add_dependency("rsync")
        # for running functional tests against local web server
        add_dependency("python-twisted-web2")
        # for generating docs from .in templates
        add_dependency("python-empy")
        # for generating .txt docs from .html
        add_dependency("lynx-cur-wrapper")
        # for the validate command
        add_dependency("wdg-html-validator")
        # for collecting code coverage data and generating coverage reports
        add_dependency("python-figleaf", ppa="jjl/figleaf")

        # for css validator
        add_dependency("sun-java6-jre")
        add_dependency("libcommons-collections3-java")
        add_dependency("libcommons-lang-java")
        add_dependency("libxerces2-java")
        add_dependency("libtagsoup-java")
        # OMG, it depends on piles of java web server stuff, even for local
        # command-line validation.  You're doing it wrong!
        add_dependency("velocity")
        dependency_actions.append(self.install_css_validator_in_release_dir)

        # for generating .html docs from .txt markdown files
        # dependencies of haskell platform
        # http://davidsiegel.org/haskell-platform-in-karmic-koala/
        for pkg in ("ghc6 ghc6-prof ghc6-doc haddock libglut-dev happy alex "
                    "libedit-dev zlib1g-dev checkinstall".split()):
            add_dependency(pkg)
        dependency_actions.append(self.install_haskell_platform_in_release_dir)
        dependency_actions.append(self.install_pandoc_in_release_dir)

        return dependency_actions

    def _make_test_step(self, env, python_version,
                        easy_install_test=True,
                        local_server=True,
                        coverage=False):
        python = "python%d.%d" % python_version
        if 0:#coverage:
            # disabled for the moment -- think I probably built the launchpad
            # .deb from wrong branch, without bug fixes
            # python-figleaf only supports Python 2.6 ATM
            assert python_version == (2, 6), python_version
            python = "figleaf"
        name = "python%s" % "".join((map(str, python_version)))
        actions = []
        def test(log):
            test_cmd = [python, "test.py"]
            if not local_server:
                test_cmd.append("--no-local-server")
                # running against wwwsearch.sourceforge.net is slow, want to
                # see where it failed
                test_cmd.append("-v")
            if coverage:
                # TODO: Fix figleaf traceback with doctests
                test_cmd.append("--skip-doctests")
            env.cmd(test_cmd)
        tests_name = "tests"
        if not local_server:
            tests_name += "_internet"
        actions.append((tests_name, test))
        import mechanize._testcase
        temp_maker = mechanize._testcase.TempDirMaker()
        temp_dir = temp_maker.make_temp_dir()
        if easy_install_test:
            def setup_py_easy_install(log):
                output = release.get_cmd_stdout(
                    cmd_env.set_environ_vars_env(
                        [("PYTHONPATH", temp_dir)], env),
                    [python, "setup.py", "easy_install", "-d", temp_dir, "."],
                    stderr=subprocess.STDOUT)
                # easy_install doesn't fail properly :-(
                if "SyntaxError" in output:
                    raise Exception(output)
                temp_maker.tear_down()
            actions.append(setup_py_easy_install)
        return action_tree.make_node(actions, name)

    def performance_test(self, log):
        result = run_performance_tests(self._repo_path)
        if not result.wasSuccessful():
            raise Exception("performance tests failed")

    def clean_coverage(self, log):
        self._in_repo.cmd(["rm", "-f", ".figleaf"])
        self._in_repo.cmd(release.rm_rf_cmd("html"))

    @action_tree.action_node
    def test(self):
        r = []
        r.append(("python26_coverage",
                  self._make_test_step(self._in_repo, python_version=(2, 6),
                                       easy_install_test=False,
                                       coverage=True)))
        r.append(self._make_test_step(self._in_repo, python_version=(2, 6)))
        r.append(self._make_test_step(self._in_repo, python_version=(2, 5)))
        # the functional tests rely on a local web server implemented using
        # twisted.web2, which depends on zope.interface, but ubuntu karmic
        # doesn't have a Python 2.4 package for zope.interface, so run them
        # against wwwsearch.sourceforge.net
        r.append(self._make_test_step(self._in_repo, python_version=(2, 4),
                                      local_server=False))
        r.append(self.performance_test)
        return r

    def make_coverage_html(self, log):
        self._in_repo.cmd(["figleaf2html"])

    def tag(self, log):
        self._in_repo.cmd(["git", "checkout", "master"])
        self._in_repo.cmd(["git", "tag",
                           "-m", "Tagging release %s" % self._release_version,
                           str(self._release_version)])

    def clean_docs(self, log):
        self._in_docs_dir.cmd(release.rm_rf_cmd("html"))

    def make_docs(self, log):
        self._in_docs_dir.cmd(["mkdir", "-p", "html"])
        site_map = release.site_map()
        def pandoc(filename, source_filename):
            last_modified = release.last_modified(source_filename,
                                                  self._in_docs_dir)
            variables = [
                ("last_modified_iso",
                 time.strftime("%Y-%m-%d", last_modified)),
                ("last_modified_month_year",
                 time.strftime("%B %Y", last_modified))]
            page_name = os.path.splitext(os.path.basename(filename))[0]
            variables.append(("nav", release.nav_html(site_map, page_name)))
            variables.append(("subnav", release.subnav_html(site_map,
                                                            page_name)))
            release.pandoc(self._in_docs_dir, filename, variables=variables)
        release.empy(self._in_docs_dir, "forms.txt.in")
        release.empy(self._in_docs_dir, "download.txt.in",
                     defines=["version=%r" % str(self._release_version)])
        for page in site_map.iter_pages():
            if page.name in ["Root", "Changelog"]:
                continue
            source_filename = filename = page.name + ".txt"
            if page.name in ["forms", "download"]:
                source_filename += ".in"
            pandoc(filename, source_filename)
        self._in_repo.cmd(["cp", "-r", "ChangeLog", "docs/html/ChangeLog.txt"])
        if self._build_tools_path is not None:
            styles = ensure_trailing_slash(
                os.path.join(self._website_source_path, "styles"))
            self._env.cmd(["rsync", "-a", styles,
                           os.path.join(self._docs_dir, "styles")])

    def write_setup_cfg(self, log):
        # write empty setup.cfg so source distribution is built using a version
        # number without ".dev" and today's date appended
        self._in_repo.cmd(cmd_env.write_file_cmd("setup.cfg", ""))

    def setup_py_sdist(self, log):
        self._in_repo.cmd(["python", "setup.py", "sdist",
                           "--formats=gztar,zip"])
        archives = set(os.listdir(os.path.join(self._repo_path, "dist")))
        assert archives == self._source_distributions, \
            (archives, self._source_distributions)

    @action_tree.action_node
    def build_sdist(self):
        return [
            self.clean_docs,
            self.make_docs,
            self.write_setup_cfg,
            self.setup_py_sdist,
            ]

    def _stage(self, path, dest_dir, dest_basename=None,
               source_base_path=None):
        # IIRC not using rsync because didn't see easy way to avoid updating
        # timestamp of unchanged files, which was upsetting git
        # note: files in the website repository that are no longer generated
        # must be manually deleted from the repository
        if source_base_path is None:
            source_base_path = self._repo_path
        full_path = os.path.join(source_base_path, path)
        try:
            self._env.cmd(["readlink", "-e", full_path],
                          stdout=open(os.devnull, "w"))
        except cmd_env.CommandFailedError:
            print "not staging (does not exist):", full_path
            return
        if dest_basename is None:
            dest_basename = os.path.basename(path)
        dest = os.path.join(self._mirror_path, dest_dir, dest_basename)
        try:
            self._env.cmd(["cmp", full_path, dest])
        except cmd_env.CommandFailedError:
            print "staging: %s -> %s" % (full_path, dest)
            self._env.cmd(["cp", full_path, dest])
        else:
            print "not staging (unchanged): %s -> %s" % (full_path, dest)

    def ensure_website_repo_unmodified(self, log):
        ensure_unmodified(self._env, self._website_source_path)

    def make_website(self, log):
        pass

    def ensure_staging_website_unmodified(self, log):
        ensure_unmodified(self._env, self._mirror_path)

    def _stage_flat_dir(self, path, dest):
        self._env.cmd(["mkdir", "-p", os.path.join(self._mirror_path, dest)])
        for filename in os.listdir(path):
            self._stage(os.path.join(path, filename), dest)

    def _symlink_flat_dir(self, path):
        for filename in os.listdir(path):
            link_dir = os.path.dirname(path)
            target = os.path.relpath(os.path.join(path, filename), link_dir)
            link_path = os.path.join(link_dir, filename)
            if not os.path.islink(link_path) or \
                    os.path.realpath(link_path) != target:
                self._env.cmd(["ln", "-f", "-s", "-t", link_dir, target])

    def collate(self, log):
        stage = self._stage
        html_dir = os.path.join(self._docs_dir, "html")
        self._stage_flat_dir(html_dir, "htdocs/mechanize/docs")
        self._symlink_flat_dir(
            os.path.join(self._mirror_path, "htdocs/mechanize/docs"))
        for archive in self._source_distributions:
            stage(os.path.join("dist", archive), "htdocs/mechanize/src")
        stage("test-tools/cookietest.cgi", "cgi-bin")
        stage("examples/forms/echo.cgi", "cgi-bin")
        stage("examples/forms/example.html", "htdocs/mechanize")
        if self._build_tools_path is not None:
            stage(os.path.join(self._website_source_path, "frontpage.html"),
                  "htdocs", "index.html")
            self._stage_flat_dir(
                os.path.join(self._website_source_path, "styles"),
                "htdocs/styles")

    def commit_staging_website(self, log):
        self._in_mirror.cmd(["git", "add", "--all"])
        self._in_mirror.cmd(
            ["git", "commit",
             "-m", "Automated update for release %s" % self._release_version])

    def validate_html(self, log):
        exclusions = set(f for f in """\
./cookietest.html
htdocs/basic_auth/index.html
htdocs/digest_auth/index.html
htdocs/mechanize/example.html
htdocs/test_fixtures/index.html
htdocs/test_fixtures/mechanize_reload_test.html
htdocs/test_fixtures/referertest.html
""".splitlines() if not f.startswith("#"))
        for dirpath, dirnames, filenames in os.walk(self._mirror_path):
            try:
                # archived website
                dirnames.remove("old")
            except ValueError:
                pass
            for filename in filenames:
                if filename.endswith(".html"):
                    page_path = os.path.join(
                        os.path.relpath(dirpath, self._mirror_path), filename)
                    if page_path not in exclusions:
                        self._in_mirror.cmd(["validate", page_path])

    def _classpath_cmd(self):
        from_packages = ["/usr/share/java/commons-collections3.jar",
                         "/usr/share/java/commons-lang.jar",
                         "/usr/share/java/xercesImpl.jar",
                         "/usr/share/java/tagsoup.jar",
                         "/usr/share/java/velocity.jar",
                         ]
        jar_dir = os.path.join(self._release_dir, self._css_validator_path)
        local = glob.glob(os.path.join(jar_dir, "*.jar"))
        path = ":".join(local + from_packages)
        return ["env", "CLASSPATH=%s" % path]

    def _sanitise_css(self, path):
        temp_dir = tempfile.mkdtemp(prefix="tmp-%s-" % self.__class__.__name__)
        def tear_down():
            shutil.rmtree(temp_dir)
        temp_path = os.path.join(temp_dir, os.path.basename(path))
        temp = open(temp_path, "w")
        try:
            for line in open(path):
                if line.rstrip().endswith("/*novalidate*/"):
                    # temp.write("/*%s*/\n" % line.rstrip())
                    temp.write("/*sanitised*/\n")
                else:
                    temp.write(line)
        finally:
            temp.close()
        return temp_path, tear_down

    def validate_css(self, log):
        env = cmd_env.PrefixCmdEnv(self._classpath_cmd(), self._in_release_dir)
        # env.cmd(["java", "org.w3c.css.css.CssValidator", "--help"])
        """
Usage: java org.w3c.css.css.CssValidator  [OPTIONS] | [URL]*
OPTIONS
	-p, --printCSS
		Prints the validated CSS (only with text output, the CSS is printed with other outputs)
	-profile PROFILE, --profile=PROFILE
		Checks the Stylesheet against PROFILE
		Possible values for PROFILE are css1, css2, css21 (default), css3, svg, svgbasic, svgtiny, atsc-tv, mobile, tv
	-medium MEDIUM, --medium=MEDIUM
		Checks the Stylesheet using the medium MEDIUM
		Possible values for MEDIUM are all (default), aural, braille, embossed, handheld, print, projection, screen, tty, tv, presentation
	-output OUTPUT, --output=OUTPUT
		Prints the result in the selected format
		Possible values for OUTPUT are text (default), xhtml, html (same result as xhtml), soap12
	-lang LANG, --lang=LANG
		Prints the result in the specified language
		Possible values for LANG are de, en (default), es, fr, ja, ko, nl, zh-cn, pl, it
	-warning WARN, --warning=WARN
		Warnings verbosity level
		Possible values for WARN are -1 (no warning), 0, 1, 2 (default, all the warnings

URL
	URL can either represent a distant web resource (http://) or a local file (file:/)
"""
        validate_cmd = ["java", "org.w3c.css.css.CssValidator"]
        for dirpath, dirnames, filenames in os.walk(self._mirror_path):
            for filename in filenames:
                if filename.endswith(".css"):
                    path = os.path.join(dirpath, filename)
                    temp_path, tear_down = self._sanitise_css(path)
                    try:
                        page_url = "file://" + temp_path
                        output = release.get_cmd_stdout(
                            env, validate_cmd + [page_url])
                        # the validator doesn't fail properly: it exits
                        # successfully on validation failure
                        if "Sorry! We found the following errors" in output:
                            raise CSSValidationError(path, output)
                    finally:
                        tear_down()

    def upload_to_pypi(self, log):
        self._in_repo.cmd(["python", "setup.py", "sdist",
                           "--formats=gztar,zip", "upload"])

    def sync_to_sf(self, log):
        assert os.path.isdir(
            os.path.join(self._mirror_path, "htdocs/mechanize"))
        self._env.cmd(["rsync", "-rlptvuz", "--exclude", "*~", "--delete",
                       ensure_trailing_slash(self._mirror_path),
                       "jjlee,wwwsearch@web.sourceforge.net:"])

    @action_tree.action_node
    def upload(self):
        r = []
        if self._mirror_path is not None:
            r.append(self.sync_to_sf)
        r.append(self.upload_to_pypi)
        return r

    def clean(self, log):
        self._env.cmd(release.rm_rf_cmd(self._release_dir))

    def write_email(self, log):
        log = release.get_cmd_stdout(self._in_repo,
                                     ["git", "log", '--pretty=format: * %s',
                                      "%s..HEAD" % self._previous_version])
        # filter out some uninteresting commits
        log = "".join(line for line in log.splitlines(True) if not
                      re.match("^ \* Update (?:changelog|version)$", line,
                               re.I))
        self._in_release_dir.cmd(cmd_env.write_file_cmd(
                "announce_email.txt", u"""\
ANN: mechanize {version} released

http://wwwsearch.sourceforge.net/mechanize/

This is a stable bugfix release.

Changes since {previous_version}:

{log}

About mechanize
=============================================

Requires Python 2.4, 2.5, or 2.6.


Stateful programmatic web browsing, after Andy Lester's Perl module
WWW::Mechanize.

Example:

import re
from mechanize import Browser

b = Browser()
b.open("http://www.example.com/")
# follow second link with element text matching regular expression
response = b.follow_link(text_regex=re.compile(r"cheese\s*shop"), nr=1)

b.select_form(name="order")
# Browser passes through unknown attributes (including methods)
# to the selected HTMLForm
b["cheeses"] = ["mozzarella", "caerphilly"]  # (the method here is __setitem__)
response2 = b.submit()  # submit current form

response3 = b.back()  # back to cheese shop
response4 = b.reload()

for link in b.forms():
       print form
# .links() optionally accepts the keyword args of .follow_/.find_link()
for link in b.links(url_regex=re.compile("python.org")):
       print link
       b.follow_link(link)  # can be EITHER Link instance OR keyword args
       b.back()


John
""".format(log=log,
           version=self._release_version,
           previous_version=self._previous_version)))

    def push_tag(self, log):
        self._in_repo.cmd(["git", "push", "git@github.com:jjlee/mechanize.git",
                           "tag", self._release_version])

    def clean_easy_install_dir(self, log):
        test_dir = self._easy_install_test_dir
        self._in_release_dir.cmd(release.rm_rf_cmd(test_dir))
        self._in_release_dir.cmd(["mkdir", "-p", test_dir])

    def _check_easy_installed_version_equals(self, version):
        try:
            output = release.get_cmd_stdout(
                self._easy_install_env,
                ["python", "-c",
                 "import mechanize; print mechanize.__version__"],
                stderr=subprocess.PIPE)
        except cmd_env.CommandFailedError:
            raise WrongVersionError(None)
        else:
            version_tuple_string = output.strip()
            assert len(version.tuple) == 6, len(version.tuple)
            if not(version_tuple_string == str(version.tuple) or
                   version_tuple_string == str(version.tuple[:-1])):
                raise WrongVersionError(version_tuple_string)

    def check_not_installed(self, log):
        try:
            self._check_easy_installed_version_equals(self._release_version)
        except WrongVersionError:
            pass
        else:
            raise WrongVersionError("Expected version != %s" %
                                    self._release_version)

    def easy_install(self, log):
        self._easy_install_env.cmd(["easy_install",
                                    "-d", self._easy_install_test_dir,
                                    "mechanize"])

    def check_easy_installed_version(self, log):
        self._check_easy_installed_version_equals(self._release_version)

    def copy_in_functional_test_dependencies(self, log):
        dst = os.path.join(self._release_dir, self._easy_install_test_dir)
        def copy_in(src):
            self._env.cmd(["cp", "-r", src, dst])
        # so that repository copy of mechanize is not on sys.path
        copy_in(os.path.join(self._repo_path, "test.py"))
        copy_in(os.path.join(self._repo_path, "test"))
        copy_in(os.path.join(self._repo_path, "test-tools"))

        expected_content = "def open_local_file(self, filename):"
        data = """\
# functional tests reads this file and expects this content:
#%s
""" % expected_content
        dirpath = os.path.join(dst, "mechanize")
        self._env.cmd(["mkdir", "-p", dirpath])
        self._env.cmd(
            cmd_env.write_file_cmd(os.path.join(dirpath, "_mechanize.py"),
                                   data))

    @action_tree.action_node
    def easy_install_test_internet(self):
        return [
            self.clean_easy_install_dir,
            self.check_not_installed,
            self.easy_install,
            self.check_easy_installed_version,
            self.copy_in_functional_test_dependencies,
            # Run in test dir, because the test step expects that.  The
            # PYTHONPATH from self._easy_install_env is wrong here because
            # we're running in the test dir rather than its parent.  That's OK
            # because the test dir is still on sys.path, for the same reason.
            self._make_test_step(release.CwdEnv(self._easy_install_env,
                                                self._easy_install_test_dir),
                                 python_version=(2, 6),
                                 easy_install_test=False,
                                 # run against wwwsearch.sourceforge.net
                                 local_server=False),
            ]

    def send_email(self, log):
        text = release.read_file_from_env(self._in_release_dir,
                                          "announce_email.txt")
        print "text %r" % text
        subject, sep, body = text.partition("\n")
        body = body.lstrip()
        assert len(body) > 0, body
        send_email(from_address="jjl@pobox.com",
                   to_address="wwwsearch-general@lists.sourceforge.net",
                   subject=subject,
                   body=body)

    @action_tree.action_node
    def build(self):
        return [
            self.clean,
            self.install_deps,
            self.print_next_tag,
            self.clone,
            self.checks,
            self.clean_coverage,
            self.test,
            self.make_coverage_html,
            self.tag,
            self.build_sdist,
            self.write_email,
            ]

    @action_tree.action_node
    def update_staging_website(self):
        r = []
        if self._build_tools_path is not None:
            r.extend([
                    self.ensure_website_repo_unmodified,
                    self.make_website,
                    ])
        if self._mirror_path is not None:
            r.extend([
                    self.ensure_staging_website_unmodified,
                    self.collate,
                    self.validate_html,
                    self.validate_css,
                    self.commit_staging_website,
                    ])
        return r

    @action_tree.action_node
    def tell_the_world(self):
        return [
            self.push_tag,
            self.upload,
            self.easy_install_test_internet,
            self.send_email,
            ]

    @action_tree.action_node
    def all(self):
        return [
            self.build,
            self.update_staging_website,
            self.tell_the_world,
            ]


def parse_options(args):
    parser = optparse.OptionParser(usage=__doc__.strip())
    release.add_basic_env_options(parser)
    parser.add_option("--git-repository", metavar="DIRECTORY",
                      help="path to mechanize git repository (default is cwd)")
    parser.add_option("--build-tools-repository", metavar="DIRECTORY",
                      help=("path of mechanize-build-tools git repository, "
                            "from which to get other website source files "
                            "(default is not to build those files)"))
    # TODO: this is actually the path of mirror/ directory in the repository
    parser.add_option("--mirror-path", metavar="DIRECTORY",
                      help=("path of local website mirror git repository "
                            "into which built files will be copied "
                            "(default is not to copy the files)"))
    parser.add_option("--in-source-repository", action="store_true",
                      dest="in_repository",
                      help=("run all commands in original repository "
                            "(specified by --git-repository), rather than in "
                            "the clone of it in the release area"))
    parser.add_option("--tag-name", metavar="TAG_NAME")
    options, remaining_args = parser.parse_args(args)
    nr_args = len(remaining_args)
    try:
        options.release_area = remaining_args.pop(0)
    except IndexError:
        parser.error("Expected at least 1 argument, got %d" % nr_args)
    if options.mirror_path is not None and not \
            os.path.exists(os.path.join(options.mirror_path, "..", ".git")):
        parser.error("incorrect mirror path")
    return options, remaining_args


def main(argv):
    if not hasattr(action_tree, "action_main"):
        sys.exit("failed to import required modules")

    options, action_tree_args = parse_options(argv[1:])
    env = release.get_env_from_options(options)
    git_repository_path = options.git_repository
    if git_repository_path is None:
        git_repository_path = os.getcwd()
    releaser = Releaser(env, git_repository_path, options.release_area,
                        options.mirror_path, options.build_tools_repository,
                        options.in_repository, options.tag_name)
    action_tree.action_main(releaser.all, action_tree_args)


if __name__ == "__main__":
    main(sys.argv)
