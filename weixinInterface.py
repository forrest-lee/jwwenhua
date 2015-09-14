#-*- coding: utf-8 -*-
import os
import sys
root = os.path.dirname(__file__)
# 两者取其一
sys.path.insert(0, os.path.join(root, 'site-packages'))
# sys.path.insert(0, os.path.join(root, 'site-packages.zip'))


import MySQLdb
from flask import Flask, g, make_response, request, session, redirect, url_for, \
     abort, render_template, flash
import math
import time
import hashlib
import xml.etree.ElementTree as ET
from wechat_sdk import WechatBasic
import urllib
import urllib2
import re
import cookielib
from bs4 import BeautifulSoup
import json


# import sys 
reload(sys)
sys.setdefaultencoding('utf-8')



# configuration
MYSQL_DB = 'flaskr'
DEBUG = True
SECRET_KEY = 'zzhilw32ij5ww44h22mjyk0mkzhzz3jylm2kzwxw'
MYSQL_USER = 'root'
MYSQL_PASS = ''
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = '3306'

# 针对SAE配置
try:
    isSae = True
    import sae.const
    from sae.mail import EmailMessage
    MYSQL_DB = sae.const.MYSQL_DB
    # DEBUG = False
    SECRET_KEY = 'zzhilw32ij5ww44h22mjyk0mkzhzz3jylm2kzwxw'
    MYSQL_USER = sae.const.MYSQL_USER
    MYSQL_PASS = sae.const.MYSQL_PASS
    MYSQL_HOST = sae.const.MYSQL_HOST
    MYSQL_PORT = sae.const.MYSQL_PORT
except ImportError:
    pass


# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
# app.config.from_envvar('FLASKR_SETTINGS', silent=True)

def connect_db():
    return MySQLdb.connect(MYSQL_HOST, MYSQL_USER, MYSQL_PASS, \
        MYSQL_DB, port = int(MYSQL_PORT), charset = 'utf8')


def parseExamTimetable(contHtml):
        examlist = []
        examTimeTable = dict()
        soup = BeautifulSoup(contHtml, from_encoding='gb2312')

        # 这么写可能会有性能问题
        for i in range(1,10):   # 10只是个人经验估计出来的一个数，一个学期考试应该不会超过10门
            if soup.find_all("td")[2 + i*8] != '':
                examTimeTable['xkkh'] = soup.find_all("td")[0 + i*8].get_text()
                examTimeTable['kcmc'] = soup.find_all("td")[1 + i*8].get_text()
                examTimeTable['xm'] = soup.find_all("td")[2 + i*8].get_text()
                examTimeTable['kssj'] = soup.find_all("td")[3 + i*8].get_text()
                examTimeTable['ksdd'] = soup.find_all("td")[4 + i*8].get_text()
                examTimeTable['ksxs'] = soup.find_all("td")[5 + i*8].get_text()
                examTimeTable['zwh'] = soup.find_all("td")[6 + i*8].get_text()
                examTimeTable['xq'] = soup.find_all("td")[7 + i*8].get_text()
                examlist.append(examTimeTable.copy())   # .copy()非常重要
        return json.dumps(examlist, ensure_ascii=False)



# 传入的conHtml需要提前先用decode解析
def parseGradeTable(contHtml, type='dict'):
    gradeList = []
    gradeTable = dict()
    soup = BeautifulSoup(contHtml).find('table',{'class':'datelist'})

    for i in range(1,100):
        try:
            gradeTable['xn'] = soup.find_all("td")[0 + i*15].get_text()
            gradeTable['xq'] = soup.find_all("td")[1 + i*15].get_text()
            gradeTable['kcdm'] = soup.find_all("td")[2 + i*15].get_text()
            gradeTable['kcmc'] = soup.find_all("td")[3 + i*15].get_text()
            gradeTable['kcxz'] = soup.find_all("td")[4 + i*15].get_text()
            gradeTable['kcgs'] = soup.find_all("td")[5 + i*15].get_text()
            gradeTable['xf'] = soup.find_all("td")[6 + i*15].get_text()
            gradeTable['jd'] = soup.find_all("td")[7 + i*15].get_text()
            gradeTable['cj'] = soup.find_all("td")[8 + i*15].get_text()
            gradeTable['fxbj'] = soup.find_all("td")[9 + i*15].get_text()
            gradeTable['bkcj'] = soup.find_all("td")[10 + i*15].get_text()
            gradeTable['cxcj'] = soup.find_all("td")[11 + i*15].get_text()
            gradeTable['kkxy'] = soup.find_all("td")[12 + i*15].get_text()
            gradeTable['bz'] = soup.find_all("td")[13 + i*15].get_text()
            gradeTable['cxbj'] = soup.find_all("td")[14 + i*15].get_text()
            gradeList.append(gradeTable.copy())
        except:
            break

    if type == 'json':
        return json.dumps(gradeList, ensure_ascii=False)
    else:
        return gradeList



'''
@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'): g.db.close()
'''

@app.route('/')
def mainPage():
    return render_template('index.html')


@app.route('/jw',methods=['GET','POST'])
def jwMain():
    return redirect(url_for('jwLogin'))


@app.route('/jw/login',methods=['GET','POST'])
def jwLogin():
    error = ""
    if request.method == 'GET':
        webpage = urllib.urlopen('http://jw2.hustwenhua.net')
        urlStr = webpage.geturl()
        fStr = urlStr[27:51]
        session['fStr'] = fStr
        chk_imag_url = 'http://jw2.hustwenhua.net/(' + fStr + ')/CheckCode.aspx'
        return render_template('jwLoginPage.html', chk_imag_url=chk_imag_url) 

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        checkcode = request.form['checkcode']

        fStr = session['fStr']
        chk_imag_url = 'http://jw2.hustwenhua.net/(' + fStr + ')/CheckCode.aspx'
        login_url = 'http://jw2.hustwenhua.net/(' + fStr +')/default2.aspx'
        baseurl = 'http://jw2.hustwenhua.net/(' + fStr + ')/xs_main.aspx?'
        mainpage_url = baseurl + 'xh=' + username

        # 设置cookie自动管理
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj)) # Login
        urllib2.install_opener(opener) 

        # 抓取登陆页面的 '__VIEWSTATE' 的值
        htmlText = opener.open(login_url).read()
        viewstate = re.findall(
            r'<input[^>]*name=\"__VIEWSTATE\"[^>]*value=\"([^"]*)\"[^>]*>', 
            htmlText, 
            re.IGNORECASE);


        # 登陆表单填写
        LoginData = {
            '__VIEWSTATE':viewstate[0],
            'txtUserName': username,
            'TextBox2': password,
            'txtSecretCode': checkcode,
            'RadioButtonList1':'%D1%A7%C9%FA',
            'Button1':'',
            'lbLanguage':'',
            'hidPdrs':'',
            'hidsc':''
        }
        login_req = urllib2.Request(login_url, urllib.urlencode(LoginData));    #登陆
        login_req.add_header('User-Agent', "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36");  
        login_response = opener.open(login_req).read()

        # 输出服务器返回信息（需要从gb2312解码）
        # 待实现功能：解析返回的html页面文本判断是否登陆成功
        # flash(login_response.decode('gb2312'))

        
        html = opener.open(mainpage_url).read()
        soup = BeautifulSoup(html, from_encoding='gb2312')
        name = soup.find("span", {"id": "xhxm"})
        try:
            nameStr = name.get_text()
        except:
            error = "用户名或密码或验证码错误"
            return render_template('jwLoginPage.html', chk_imag_url=chk_imag_url, error=error)
            nameStr = u"姓名空"
        
        name = nameStr.replace(u'同学','')
        session['logged_in'] = username
        session['name'] = name
        flash(u"欢迎你，" + name + u"同学！")
        
        photoUrl = 'http://jw2.hustwenhua.net/(' + fStr +')/readimagexs.aspx?xh=' + username
        
        '''
        # 抓取课表信息
        contUrl = 'http://jw2.hustwenhua.net/(' + fStr +')/xskbcx.aspx?xh='
        + username + '&xm=' + name + '&gnmkdm=N121602'
        conReq = urllib2.Request(contUrl)
        conReq.add_header("Referer",mainpage_url)
        contHtml = opener.open(conReq).read()

        # 抓取考试信息
        contUrl = 'http://jw2.hustwenhua.net/(' + fStr +')/xskscx.aspx?xh=' 
        + username + '&xm=' + name + '&gnmkdm=N121603'
        conReq = urllib2.Request(contUrl)
        conReq.add_header("Referer", mainpage_url)
        contHtml = opener.open(conReq).read()
        timetable = BeautifulSoup(contHtml, from_encoding='gb2312')
        # timetable = parseExamTimetable(contHtml)
        '''

        # 历年成绩抓取
        grade_url = 'http://jw2.hustwenhua.net/(' + fStr +')/xscjcx.aspx?xh=' + username + '&xm=' + name + '&gnmkdm=N121613'
        grade_req = urllib2.Request(grade_url);
        grade_req.add_header("Referer", mainpage_url)
        grade_response = opener.open(grade_req).read().decode('gbk','ignore')
        htmlText = BeautifulSoup(grade_response)
        # 用BeautifulSoup解码，在SAE上运行时会出现获取到的body标签内容为空的奇怪bug
        # 解决方案就是改用 .decode('gbk')来解码
        # grade_response = opener.open(grade_req).read()
        # htmlText = BeautifulSoup(grade_response, from_encoding='gb2312')

        viewstate = re.findall('<input[^>]*name=\"__VIEWSTATE\"[^>]*value=\"([^"]*)\"[^>]*>', 
            str(htmlText), 
            re.IGNORECASE);

        postData = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate[0],
            'hidLanguage': '',
            'ddlXN': '',
            'ddlXQ': '',
            'ddl_kcxz': '',
            'btn_zcj': '%C0%FA%C4%EA%B3%C9%BC%A8'
        }
        grade_req = urllib2.Request(grade_url, urllib.urlencode(postData));
        grade_req.add_header("Referer", grade_url)
        grade_req.add_header('User-Agent', "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36");  
        grade_response = opener.open(grade_req).read().decode('gbk','ignore')
        contHtml = BeautifulSoup(grade_response).find_all('table')
        parsedTable = parseGradeTable(str(contHtml))
           
        return render_template('jwMainPage.html', user_imag_url=photoUrl, name=name, cont=parsedTable)
    

@app.route('/jw/grades')
def jwGrades():
    if 'logged_in' not in session:
        return redirect(url_for('jwLogin'))
    error = ""
    fStr = session['fStr']
    username = session['logged_in']
    name = session['name']
    photoUrl = 'http://jw2.hustwenhua.net/(' + fStr +')/readimagexs.aspx?xh=' + username

    baseurl = 'http://jw2.hustwenhua.net/(' + fStr + ')/xs_main.aspx?'
    mainpage_url = baseurl + 'xh=' + username

    # 设置cookie自动管理
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj)) # Login
    urllib2.install_opener(opener) 

    # 历年成绩抓取
    grade_url = 'http://jw2.hustwenhua.net/(' + fStr +')/xscjcx.aspx?xh=' + username + '&xm=' + name + '&gnmkdm=N121613'
    grade_req = urllib2.Request(grade_url);
    grade_req.add_header("Referer", mainpage_url)
    grade_response = opener.open(grade_req).read().decode('gbk','ignore')
    htmlText = BeautifulSoup(grade_response)
    # 用BeautifulSoup解码，在SAE上运行时会出现获取到的body标签内容为空的奇怪bug
    # 解决方案就是改用 .decode('gbk')来解码
    # grade_response = opener.open(grade_req).read()
    # htmlText = BeautifulSoup(grade_response, from_encoding='gb2312')

    viewstate = re.findall('<input[^>]*name=\"__VIEWSTATE\"[^>]*value=\"([^"]*)\"[^>]*>', 
        str(htmlText), 
        re.IGNORECASE);

    postData = {
        '__EVENTTARGET': '',
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': viewstate[0],
        'hidLanguage': '',
        'ddlXN': '',
        'ddlXQ': '',
        'ddl_kcxz': '',
        'btn_zcj': '%C0%FA%C4%EA%B3%C9%BC%A8'
    }
    grade_req = urllib2.Request(grade_url, urllib.urlencode(postData));
    grade_req.add_header("Referer", grade_url)
    grade_req.add_header('User-Agent', "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36");  
    grade_response = opener.open(grade_req).read().decode('gbk','ignore')
    contHtml = BeautifulSoup(grade_response).find_all('table')
    parsedTable = parseGradeTable(str(contHtml))
       
    return render_template('jwMainPage.html', user_imag_url=photoUrl, name=name, cont=parsedTable)


@app.route('/jw/timetable')
def jwTimetable():
    if 'logged_in' not in session:
        return redirect(url_for('jwLogin'))

    error = ""
    fStr = session['fStr']
    username = session['logged_in']
    name = session['name']

    baseurl = 'http://jw2.hustwenhua.net/(' + fStr + ')/xs_main.aspx?'
    mainpage_url = baseurl + 'xh=' + username

    # 设置cookie自动管理
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj)) # Login
    urllib2.install_opener(opener) 

    # 抓取课表信息
    contUrl = 'http://jw2.hustwenhua.net/(' + fStr +')/xskbcx.aspx?xh=' + username + '&xm=' + name + '&gnmkdm=N121602'
    conReq = urllib2.Request(contUrl)
    conReq.add_header("Referer",mainpage_url)
    contHtml = opener.open(conReq).read().decode('gbk', 'ignore')

    return render_template('jwTimetable.html', timetable=contHtml)



@app.route('/jw/logout')
def jwLogout():
    session['login'] = False
    return redirect('jwMainPage.html')



@app.route('/jw/sendMail',methods=['POSt'])
def sendMail():
    recvAdd = request.args['emailAddress']



@app.errorhandler(404) 
def page_not_found(error): 
    return render_template('page_not_found.html')




@app.route('/weixin',methods=['GET','POST'])
def wechat_auth():
    if request.method == 'GET':
        token='hustxunli'
        data = request.args
        signature = data.get('signature','')
        timestamp = data.get('timestamp','')
        nonce = data.get('nonce','')
        echostr = data.get('echostr','')
        s = [timestamp,nonce,token]
        s.sort()
        s = ''.join(s)
        if (hashlib.sha1(s).hexdigest() == signature):
            return make_response(echostr)
    else:
        rec = request.stream.read()
        xml_rec = ET.fromstring(rec)
        tou = xml_rec.find('ToUserName').text
        fromu = xml_rec.find('FromUserName').text
        content = xml_rec.find('Content').text
        
        contentText = content.split('#')
        
        
        xml_rep_text = """<xml>
            <ToUserName><![CDATA[%s]]></ToUserName>
            <FromUserName><![CDATA[%s]]></FromUserName>
            <CreateTime>%s</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[%s]]></Content>
            <FuncFlag>0</FuncFlag>
            </xml>"""
        xml_rep_img = """<xml>
            <ToUserName><![CDATA[%s]]></ToUserName>
            <FromUserName><![CDATA[%s]]></FromUserName>
            <CreateTime>%s</CreateTime>
            <MsgType><![CDATA[news]]></MsgType>
            <ArticleCount>1</ArticleCount><Articles>
            <item>
            <Title><![CDATA[%s]]></Title>
            <Description><![CDATA[%s]]></Description>
            <PicUrl><![CDATA[%s]]></PicUrl>
            </item>
            </Articles>
            <FuncFlag>1</FuncFlag>
            </xml>"""
        

        if content[0] == "help":
            replyContent = "checkcode：获取教务网登陆验证码"
            response = make_response(xml_rep_text % (fromu,tou,str(int(time.time())), replyContent))
            response.content_type='application/xml'
        elif contentText[0] == "checkcode":
            msg_title = u"验证码"
            msgcontent = u"您获取的是华中科技大学文华学院教务网登陆的4位验证码"
            webpage = urllib.urlopen('http://jw2.hustwenhua.net')
            urlStr = webpage.geturl()
            fStr = urlStr[27:51]
            msg_imag_url = 'http://jw2.hustwenhua.net/(' + fStr + ')/CheckCode.aspx'
            response = make_response(xml_rep_img % (fromu,tou,str(int(time.time())), 
                msg_title, msgcontent, msg_imag_url))
            response.content_type='application/xml'
        elif contentText[0] == 'login':
            checkcode = contentText[1]
            replyContent = u"您输入的验证码是：" + contentText[1]
            response = make_response(xml_rep_text % (fromu,tou,str(int(time.time())), replyContent))
            response.content_type='application/xml'
        else:
            replyContent = "来了？坐。\n本公众号目前还在开发中，回复help查看帮助列表"
            response = make_response(xml_rep_text % (fromu,tou,str(int(time.time())), replyContent))
            response.content_type='application/xml'
    
        return response


if __name__ == '__main__':
    app.run(debug=True)

