import mechanize
# sample https://www.pythonforbeginners.com/python-on-the-web/browsing-in-python-with-mechanize/
br = mechanize.Browser()
br.set_debug_http(True)
br.addheaders = [(b'user-agent',
                  b'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.3) Gecko/20100423 Ubuntu/10.04 (lucid) Firefox/3.6.3'),
                 (b'accept', b'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')]
br.set_handle_robots(False)
r = br.open("https://www.google.com/")
print(r.get_data())
exit(1)
print(r.code)
for f in br.forms():
    print(f)
br.select_form('f')
br.form['q'] = 'www.foofighters.com'
br.submit()
resp = None
for link in br.links():
    print(link)
    if "www.foofighters.com" in link.url:
        resp = br.follow_link(link)
        break
content = resp.get_data()
print(content)