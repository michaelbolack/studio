"""Mississippi county jurisdiction index."""
MISSISSIPPI_COUNTIES={
"28001":"Adams","28003":"Alcorn","28005":"Amite","28007":"Attala","28009":"Benton","28011":"Bolivar","28013":"Calhoun","28015":"Carroll","28017":"Chickasaw","28019":"Choctaw","28021":"Claiborne","28023":"Clarke","28025":"Clay","28027":"Coahoma","28029":"Copiah","28031":"Covington","28033":"DeSoto","28035":"Forrest","28037":"Franklin","28039":"George","28041":"Greene","28043":"Grenada","28045":"Hancock","28047":"Harrison","28049":"Hinds","28051":"Holmes","28053":"Humphreys","28055":"Issaquena","28057":"Itawamba","28059":"Jackson","28061":"Jasper","28063":"Jefferson","28065":"Jefferson Davis","28067":"Jones","28069":"Kemper","28071":"Lafayette","28073":"Lamar","28075":"Lauderdale","28077":"Lawrence","28079":"Leake","28081":"Lee","28083":"Leflore","28085":"Lincoln","28087":"Lowndes","28089":"Madison","28091":"Marion","28093":"Marshall","28095":"Monroe","28097":"Montgomery","28099":"Neshoba","28101":"Newton","28103":"Noxubee","28105":"Oktibbeha","28107":"Panola","28109":"Pearl River","28111":"Perry","28113":"Pike","28115":"Pontotoc","28117":"Prentiss","28119":"Quitman","28121":"Rankin","28123":"Scott","28125":"Sharkey","28127":"Simpson","28129":"Smith","28131":"Stone","28133":"Sunflower","28135":"Tallahatchie","28137":"Tate","28139":"Tippah","28141":"Tishomingo","28143":"Tunica","28145":"Union","28147":"Walthall","28149":"Warren","28151":"Washington","28153":"Wayne","28155":"Webster","28157":"Wilkinson","28159":"Winston","28161":"Yalobusha","28163":"Yazoo"
}

def validate_mississippi_counties():
    if len(MISSISSIPPI_COUNTIES)!=82: raise ValueError("Mississippi county index must contain exactly 82 counties")
    if any(len(k)!=5 or not k.startswith("28") or not k.isdigit() for k in MISSISSIPPI_COUNTIES): raise ValueError("invalid Mississippi county FIPS")
    if len(set(MISSISSIPPI_COUNTIES.values()))!=82: raise ValueError("duplicate Mississippi county name")
    return True
