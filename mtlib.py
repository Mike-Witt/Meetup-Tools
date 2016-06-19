#
# Meetup Tools Library
#

# get_page()
#
# Return the page specified by "url"
#
def get_page(url):
    import mechanize
    br = mechanize.Browser()
    br.set_handle_robots(False)
    br.set_handle_equiv(False)
    br.addheaders = [('User-agent', 'Mozilla/5.0')]
    response = br.open(url)
    return(response.read())

# locate_and_extract()
#
# First skip text until you have read "locator." Then extract the text
# between "start" and "end" and return it. For example, if you have
# something like this:
#
# <div class="price">
# <b>Price in dollars: $29.95</b>
# </div>
#
# and you just want the actual number 29.95, you could do:
# locate_and_extract(page, '<div class="price">', ': $', '</b>')
#
def locate_and_extract(page, locator, start, end):
    try:
        ptr = page.index(locator)
        page = page[ptr+len(locator):]
        ptr = page.index(start)
        page = page[ptr+len(start):]
        ptr = page.index(end)
    except:
        return('', '')
    value = page[:ptr]
    page = page[ptr+len(end):]
    return(page, value)
