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


def is_git_repository(path):
    return os.path.exists(os.path.join(path, ".git"))


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


def clean_dir(env, path):
    env.cmd(release.rm_rf_cmd(path))
    env.cmd(["mkdir", "-p", path])


class EasyInstallTester(object):

    def __init__(self, env, install_dir, project_name,
                 test_cmd, expected_version=None,
                 easy_install_cmd=("easy_install",)):
        self._env = env
        self._install_dir = install_dir
        self._project_name = project_name
        self._test_cmd = test_cmd
        self._expected_version = expected_version
        self._easy_install_cmd = list(easy_install_cmd)
        self._install_dir_on_pythonpath = cmd_env.set_environ_vars_env(
            [("PYTHONPATH", self._install_dir)], env)

    def clean_install_dir(self, log):
        clean_dir(self._env, self._install_dir)

    def _check_version_equals(self, version):
        try:
            output = release.get_cmd_stdout(
                self._install_dir_on_pythonpath,
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
            self._check_version_equals(self._expected_version)
        except WrongVersionError:
            pass
        else:
            raise WrongVersionError("Expected version != %s" %
                                    self._expected_version)

    def easy_install(self, log):
        output = release.get_cmd_stdout(
            self._install_dir_on_pythonpath,
            self._easy_install_cmd + ["-d", self._install_dir,
                                      self._project_name])
        # easy_install doesn't fail properly :-(
        if "SyntaxError" in output:
            raise Exception(output)

    def check_installed_version(self, log):
        self._check_version_equals(self._expected_version)

    def test(self, log):
        self._install_dir_on_pythonpath.cmd(self._test_cmd)

    @action_tree.action_node
    def easy_install_test(self):
        return [
            self.clean_install_dir,
            self.check_not_installed,
            self.easy_install,
            self.check_installed_version,
            self.test,
            ]


def make_source_dist_easy_install_test_step(env, install_dir,
                                            source_dir,
                                            test_cmd, expected_version):
    tester = EasyInstallTester(
        env,
        install_dir,
        project_name=".",
        test_cmd=test_cmd,
        expected_version=expected_version,
        easy_install_cmd=(cmd_env.in_dir(source_dir) +
                          ["python", "setup.py", "easy_install"]))
    return tester.easy_install_test


def make_pypi_easy_install_test_step(env, install_dir,
                                     test_cmd, expected_version):
    tester = EasyInstallTester(
        env,
        install_dir,
        project_name="mechanize",
        test_cmd=test_cmd,
        expected_version=expected_version)
    return tester.easy_install_test


def make_tarball_easy_install_test_step(env, install_dir,
                                        tarball_path,
                                        test_cmd, expected_version):
    tester = EasyInstallTester(
        env,
        install_dir,
        project_name=tarball_path,
        test_cmd=test_cmd,
        expected_version=expected_version)
    return tester.easy_install_test


class Releaser(object):

    def __init__(self, env, git_repository_path, release_dir, mirror_path,
                 build_tools_repo_path=None, run_in_repository=False,
                 tag_name=None, test_uri=None):
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
        self._css_validator_path = "css-validator"
        self._test_uri = test_uri
        self._functional_test_deps_dir = os.path.join(release_dir,
                                                      "functional_test_deps")
        self._easy_install_test_dir = os.path.join(release_dir,
                                                   "easy_install_test")
        self._in_easy_install_dir = release.CwdEnv(self._env,
                                                   self._easy_install_test_dir)
        # prevent anything other than functional test dependencies being on
        # sys.path due to cwd or PYTHONPATH
        self._easy_install_env = cmd_env.clean_environ_except_home_env(
            release.CwdEnv(env, self._functional_test_deps_dir))
        self._zope_testbrowser_dir = os.path.join(release_dir,
                                                  "zope_testbrowser_test")

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
        for path in ["ChangeLog", "mechanize/_version.py"]:
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
        clean_dir(self._env, jar_dir)
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
        # for running zope_testbrowser tests
        add_dependency("python-virtualenv")
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

    def copy_functional_test_dependencies(self, log):
        # so test.py can be run without the mechanize alongside it being on
        # sys.path
        # TODO: move mechanize package into a top-level directory, so it's not
        # automatically on sys.path
        def copy_in(src):
            self._env.cmd(["cp", "-r", src, self._functional_test_deps_dir])
        clean_dir(self._env, self._functional_test_deps_dir)
        copy_in(os.path.join(self._repo_path, "test.py"))
        copy_in(os.path.join(self._repo_path, "test"))
        copy_in(os.path.join(self._repo_path, "test-tools"))
        copy_in(os.path.join(self._repo_path, "examples"))

    def _make_test_cmd(self, python_version,
                       local_server=True,
                       uri=None,
                       coverage=False):
        python = "python%d.%d" % python_version
        if coverage:
            # python-figleaf only supports Python 2.6 ATM
            assert python_version == (2, 6), python_version
            python = "figleaf"
        test_cmd = [python, "test.py"]
        if not local_server:
            test_cmd.append("--no-local-server")
            # running against wwwsearch.sourceforge.net is slow, want to
            # see where it failed
            test_cmd.append("-v")
        if coverage:
            # TODO: Fix figleaf traceback with doctests
            test_cmd.append("--skip-doctests")
        if uri is not None:
            test_cmd.extend(["--uri", uri])
        return test_cmd

    def performance_test(self, log):
        result = run_performance_tests(self._repo_path)
        if not result.wasSuccessful():
            raise Exception("performance tests failed")

    def clean_coverage(self, log):
        self._in_repo.cmd(["rm", "-f", ".figleaf"])
        self._in_repo.cmd(release.rm_rf_cmd("html"))

    def _make_test_step(self, env, *args, **kwds):
        test_cmd = self._make_test_cmd(*args, **kwds)
        def test_step(log):
            env.cmd(test_cmd)
        return test_step

    def _make_easy_install_test_cmd(self, *args, **kwds):
        test_cmd = self._make_test_cmd(*args, **kwds)
        test_cmd.extend(
            ["discover",
             "--start-directory", self._functional_test_deps_dir])
        return test_cmd

    def _make_source_dist_easy_install_test_step(self, env, *args, **kwds):
        test_cmd = self._make_easy_install_test_cmd(*args, **kwds)
        return make_source_dist_easy_install_test_step(
            self._easy_install_env, self._easy_install_test_dir,
            self._repo_path, test_cmd, self._release_version)

    def _make_pypi_easy_install_test_step(self, env, *args, **kwds):
        test_cmd = self._make_easy_install_test_cmd(*args, **kwds)
        return make_pypi_easy_install_test_step(
            self._easy_install_env, self._easy_install_test_dir,
            test_cmd, self._release_version)

    def _make_tarball_easy_install_test_step(self, env, *args, **kwds):
        test_cmd = self._make_easy_install_test_cmd(*args, **kwds)
        [tarball] = list(d for d in self._source_distributions if
                         d.endswith(".tar.gz"))
        return make_tarball_easy_install_test_step(
            self._easy_install_env, self._easy_install_test_dir,
            os.path.abspath(os.path.join("dist", tarball)),
            test_cmd, self._release_version)

    @action_tree.action_node
    def test(self):
        r = []
        r.append(("python26_test",
                  self._make_test_step(self._in_repo, python_version=(2, 6))))
        # disabled for the moment -- think I probably built the launchpad .deb
        # from wrong branch, without bug fixes
        # r.append(("python26_coverage",
        #           self._make_test_step(self._in_repo, python_version=(2, 6),
        #                                coverage=True)))
        r.append(("python26_easy_install_test",
                  self._make_source_dist_easy_install_test_step(
                    self._in_repo, python_version=(2, 6))))
        r.append(("python25_easy_install_test",
                  self._make_source_dist_easy_install_test_step(
                    self._in_repo, python_version=(2, 5))))
        # the functional tests rely on a local web server implemented using
        # twisted.web2, which depends on zope.interface, but ubuntu karmic
        # doesn't have a Python 2.4 package for zope.interface, so run them
        # against external website
        r.append(("python24_easy_install_test_internet",
                  self._make_source_dist_easy_install_test_step(
                    self._in_repo, python_version=(2, 4),
                    local_server=False, uri=self._test_uri)))
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

    def clean_dist(self, log):
        self._in_repo.cmd(release.rm_rf_cmd("dist"))

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
            self.clean_dist,
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

    def _symlink_flat_dir(self, path, exclude):
        for filename in os.listdir(path):
            if filename in exclude:
                continue
            link_dir = os.path.dirname(path)
            target = os.path.relpath(os.path.join(path, filename), link_dir)
            link_path = os.path.join(link_dir, filename)
            if not os.path.islink(link_path) or \
                    os.path.realpath(link_path) != target:
                self._env.cmd(["ln", "-f", "-s", "-t", link_dir, target])

    def collate(self):
        html_dir = os.path.join(self._docs_dir, "html")
        self._stage_flat_dir(html_dir, "htdocs/mechanize/docs")
        self._symlink_flat_dir(
            os.path.join(self._mirror_path, "htdocs/mechanize/docs"),
            exclude=[".git", ".htaccess", ".svn", "CVS"])
        self._stage("test-tools/cookietest.cgi", "cgi-bin")
        self._stage("examples/forms/echo.cgi", "cgi-bin")
        self._stage("examples/forms/example.html", "htdocs/mechanize")
        if self._build_tools_path is not None:
            self._stage(
                os.path.join(self._website_source_path, "frontpage.html"),
                "htdocs", "index.html")
            self._stage_flat_dir(
                os.path.join(self._website_source_path, "styles"),
                "htdocs/styles")
        for archive in self._source_distributions:
            placeholder = os.path.join("htdocs/mechanize/src", archive)
            self._in_mirror.cmd(["touch", placeholder])

    def collate_pypi_upload_built_items(self, log):
        for archive in self._source_distributions:
            self._stage(os.path.join("dist", archive), "htdocs/mechanize/src")

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

    def fetch_zope_testbrowser(self, log):
        clean_dir(self._env, self._zope_testbrowser_dir)
        in_testbrowser = release.CwdEnv(self._env, self._zope_testbrowser_dir)
        in_testbrowser.cmd(["easy_install", "--editable",
                            "--build-directory", ".",
                            "zope.testbrowser[test]"])
        in_testbrowser.cmd(
            ["virtualenv", "--no-site-packages", "zope.testbrowser"])
        project_dir = os.path.join(self._zope_testbrowser_dir,
                                   "zope.testbrowser")
        in_project_dir = release.CwdEnv(self._env, project_dir)
        in_project_dir.cmd(
            ["sed", "-i", "-e", "s/mechanize[^\"']*/mechanize/", "setup.py"])
        in_project_dir.cmd(["bin/easy_install", "zc.buildout"])
        in_project_dir.cmd(["bin/buildout", "init"])
        [mechanize_tarball] = list(d for d in self._source_distributions if
                                   d.endswith(".tar.gz"))
        tarball_path = os.path.join(self._repo_path, "dist", mechanize_tarball)
        in_project_dir.cmd(["bin/easy_install", tarball_path])
        in_project_dir.cmd(["bin/buildout", "install"])

    def test_zope_testbrowser(self, log):
        project_dir = os.path.join(self._zope_testbrowser_dir,
                                   "zope.testbrowser")
        self._env.cmd(cmd_env.in_dir(project_dir) + ["bin/test"])

    @action_tree.action_node
    def zope_testbrowser(self):
        return [self.fetch_zope_testbrowser,
                self.test_zope_testbrowser,
                ]

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
        r.append(self.upload_to_pypi)
        # setup.py upload requires sdist command to upload zip files, and the
        # sdist comment insists on rebuilding source distributions, so it's not
        # possible to use the upload command to upload the already-built zip
        # file.  Work around that by copying the rebuilt source distributions
        # into website repository again so don't end up with two different sets
        # of source distributions with different md5 sums due to timestamps in
        # the archives.
        r.append(self.collate_pypi_upload_built_items)
        r.append(self.commit_staging_website)

        if self._mirror_path is not None:
            r.append(self.sync_to_sf)
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
                           "tag", str(self._release_version)])

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
            # self.clean_coverage,
            self.copy_functional_test_dependencies,
            self.test,
            # self.make_coverage_html,
            self.tag,
            self.build_sdist,
            ("easy_install_test", self._make_tarball_easy_install_test_step(
                    self._in_repo, python_version=(2, 6),
                    local_server=False, uri=self._test_uri)),
            self.zope_testbrowser,
            self.write_email,
            ]

    def update_version(self, log):
        version_path = "mechanize/_version.py"
        template = """\
"%(text)s"
__version__ = %(tuple)s
"""
        old_text = release.read_file_from_env(self._in_source_repo,
                                              version_path)
        old_version = old_text.splitlines()[0].strip(' "')
        assert old_version == str(self._release_version), \
            (old_version, str(self._release_version))
        def version_text(version):
            return template % {"text": str(version),
                               "tuple": repr(tuple(version.tuple[:-1]))}
        assert old_text == version_text(release.parse_version(old_version)), \
            (old_text, version_text(release.parse_version(old_version)))
        self._in_source_repo.cmd(cmd_env.write_file_cmd(
                version_path,
                version_text(self._release_version.next_version())))
        self._in_source_repo.cmd(["git", "commit", "-m", "Update version",
                                  version_path])

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
            ("easy_install_test_internet",
             self._make_pypi_easy_install_test_step(
                    self._in_repo, python_version=(2, 6),
                    local_server=False,
                    uri="http://wwwsearch.sourceforge.net/")),
            self.send_email,
            ]

    @action_tree.action_node
    def all(self):
        return [
            self.build,
            self.update_staging_website,
            self.update_version,
            self.tell_the_world,
            ]


def parse_options(args):
    parser = optparse.OptionParser(usage=__doc__.strip())
    release.add_basic_env_options(parser)
    parser.add_option("--mechanize-repository", metavar="DIRECTORY",
                      dest="git_repository_path",
                      help="path to mechanize git repository (default is cwd)")
    parser.add_option("--build-tools-repository", metavar="DIRECTORY",
                      help=("path of mechanize-build-tools git repository, "
                            "from which to get other website source files "
                            "(default is not to build those files)"))
    parser.add_option("--website-repository", metavar="DIRECTORY",
                      dest="mirror_path",
                      help=("path of local website mirror git repository into "
                            "which built files will be copied (default is not "
                            "to copy the files)"))
    parser.add_option("--in-source-repository", action="store_true",
                      dest="in_repository",
                      help=("run all commands in original repository "
                            "(specified by --git-repository), rather than in "
                            "the clone of it in the release area"))
    parser.add_option("--tag-name", metavar="TAG_NAME")
    parser.add_option("--uri", default="http://wwwsearch.sourceforge.net/",
                      help=("base URI to run tests against when not using a "
                            "built-in web server"))
    options, remaining_args = parser.parse_args(args)
    nr_args = len(remaining_args)
    try:
        options.release_area = remaining_args.pop(0)
    except IndexError:
        parser.error("Expected at least 1 argument, got %d" % nr_args)
    if options.git_repository_path is None:
        options.git_repository_path = os.getcwd()
    if not is_git_repository(options.git_repository_path):
        parser.error("incorrect git repository path")
    if not is_git_repository(options.build_tools_repository):
        parser.error("incorrect mechanize-build-tools repository path")
    mirror_path = options.mirror_path
    if mirror_path is not None:
        if not is_git_repository(options.mirror_path):
            parser.error("mirror path is not a git reporsitory")
        mirror_path = os.path.join(mirror_path, "mirror")
        if not os.path.isdir(mirror_path):
            parser.error("%r does not exist" % mirror_path)
    options.mirror_path = mirror_path
    return options, remaining_args


def main(argv):
    if not hasattr(action_tree, "action_main"):
        sys.exit("failed to import required modules")

    options, action_tree_args = parse_options(argv[1:])
    env = release.get_env_from_options(options)
    releaser = Releaser(env, options.git_repository_path, options.release_area,
                        options.mirror_path, options.build_tools_repository,
                        options.in_repository, options.tag_name, options.uri)
    action_tree.action_main(releaser.all, action_tree_args)


if __name__ == "__main__":
    main(sys.argv)
