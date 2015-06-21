import lxml.html.diff
import lxml.html
from selenium import webdriver
from bs4 import UnicodeDammit
import tldextract
import re
import requests
# HTML(filename='/tmp/seleniumStringPage.html') 

from lxml.html.clean import Cleaner
    
cleaner = Cleaner()
cleaner.javascript = True 
cleaner.style = True   
#cleaner.kill_tags = ['a', 'h1']
#cleaner.remove_tags = ['p']

def slugify(value):
    return re.sub(r'[^\w\s-]', '', re.sub(r'[-\s]+', '-', value)).strip().lower() 

def view_html(x):
    import time
    import webbrowser
    import tempfile
    with tempfile.NamedTemporaryFile('r+', suffix = '.html') as f:
        f.write(x)
        f.flush()
        webbrowser.open('file://' + f.name) 
        time.sleep(1) 

def view_node(node, attach_head = False, questionContains = None): 
    newstr = makeParentLine(node, attach_head, questionContains) 
    view_tree(newstr) 
    
def view_tree(node): 
    view_html(lxml.html.tostring(node).decode('utf8')) 

def view_diff(obj1, obj2, url = '', diffMethod = lxml.html.diff.htmldiff):
    if isinstance(obj1, str):
        tree1 = lxml.html.fromstring(obj1)
        tree2 = lxml.html.fromstring(obj2)
        html1 = obj1
        html2 = obj2
    else:
        html1 = lxml.html.tostring(obj1).decode('utf8')
        html2 = lxml.html.tostring(obj2).decode('utf8')
        tree1 = obj1
        tree2 = obj2
    diffHtml = diffMethod(tree1, tree2)
    diffTree = lxml.html.fromstring(diffHtml)
    insCounts = diffTree.xpath('count(//ins)')
    delCounts = diffTree.xpath('count(//del)')
    pureDiff = '' 
    for y in [z for z in diffTree.iter() if z.tag in ['ins', 'del']]:
        if y.text is not None:
            color = 'lightgreen' if 'ins' in y.tag else 'red'
            pureDiff += '<div style="background-color:{};">{}</div>'.format(color, y.text) 
    print('From t1 to t2, {} insertions and {} deleted'.format(insCounts, delCounts)) 
    diff = '<head><title>diff</title><base href=' + url + ' target="_blank"><style>ins{ background-color:lightgreen; } del{background-color:red;}</style></head>' +  diffHtml
    view_html(diff) 
    view_html(html1) 
    view_html(html2) 
    view_html('<html><body>{}</body></html>'.format(str(pureDiff)))     
        
def makeParentLine(node, attach_head = False, questionContains = None):
    # Add how much text context is given. e.g. 2 would mean 2 parent's text nodes are also displayed
    if questionContains is not None:
        newstr = doesThisElementContain(questionContains, lxml.html.tostring(node))    
    else:
        newstr = lxml.html.tostring(node)        
    parent = node.getparent()
    while parent is not None:
        if attach_head and parent.tag == 'html': 
            newstr = lxml.html.tostring(parent.find('.//head'), encoding='utf8').decode('utf8') + newstr
        tag, items = parent.tag, parent.items()
        attrs = " ".join(['{}="{}"'.format(x[0], x[1]) for x in items if len(x) == 2])
        newstr = '<{} {}>{}</{}>'.format(tag, attrs, newstr, tag)
        parent = parent.getparent()
    return newstr    

def extractDomain(url): 
    tld = ".".join([x for x in tldextract.extract(url) if x ])
    protocol = url.split('//', 1)[0]
    if 'file:' == protocol:
        protocol += '///'
    else:
        protocol += '//'
    return protocol + tld    

def addBaseTag(node, url): 
    root = node.getroottree()
    if not root.find('.//base'):
        head = root.find('.//head')
        base = lxml.html.Element('base', attrib = {'href' : extractDomain(url)})
        head.insert(0, base)     

def doesThisElementContain(text = 'pagination', nodeStr = ''):
    templ = '<div style="border:2px solid lightgreen"><div style="background-color:lightgreen">Does this element contain <b>{}</b>?</div>{}</div>'
    return templ.format(text, nodeStr)


# url = 'https://www.kaggle.com/c/otto-group-product-classification-challenge/forums'
# driver = webdriver.Firefox()
# driver.get(url)
# html = driver.page_source
# driver.close()

# tree3 = lxml.html.fromstring(html)
# addBaseTag(tree3, url)
# lxml.html.tostring(head)

# viewNode(tree3, True, 'pagination', save=True)


def makeTree(html, url, add_base = False):

    ud = UnicodeDammit(html, is_html=True)
    #tree = lxml.html.fromstring(cleaner.clean_html(ud.unicode_markup), base_url = extractDomain(url))
    tree = lxml.html.fromstring(ud.unicode_markup, base_url = extractDomain(url))

    for el in tree.iter():

        # remove comments
        if isinstance(el, lxml.html.HtmlComment):
            el.getparent().remove(el)
            continue

        if el.tag == 'script':
            el.getparent().remove(el)
            continue
        
    if add_base: 
        addBaseTag(tree, url)

    return tree

def getQuickTree(url):
    r = requests.get(url)
    return makeTree(r.text, url)

    
def normalize(s): 
    return re.sub(r'\s+', lambda x: '\n' if '\n' in x.group(0) else ' ', s).strip()

def get_text_and_tail(node):
    text = node.text if node.text else ''
    tail = node.tail if node.tail else ''
    return text + ' ' + tail
    
    

def fscore(x,y):
    try:
        z = sum([w in y for w in x]) / len(x)
        z2 = sum([w in x for w in y]) / len(y)
        return (2 * z * z2) / (z + z2)
    except:
        return 0

def get_pagination(tree):
    links = [(x, x.attrib['href']) for x in tree.xpath('//a') if 'href' in x.attrib]
    res = [re.findall('[0-9]+', x[1]) for x in links]
    for num, (link, x, y, z) in enumerate(zip(links[:-2], res[:-2], res[1:-1], res[2:])):
        if x and y and z:
            if len(x) == len(y) == len(z):
                for i,j,k in zip(x,y,z):
                    if int(i) + 1 == int(j) and int(i) + 2 == int(k):
                        return (link[0], find_common_ancestor(links[num][0], links[num+1][0]))

def find_common_ancestor(n1, n2):
    if n1 is n2:
        return n1.getparent()
    n1_ancestors = set(n1.iterancestors())
    for parent in n2.iterancestors():
        if parent in n1_ancestors:
            return parent
