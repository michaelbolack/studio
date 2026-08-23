"""Alabama county jurisdiction index for national Election Center onboarding."""
ALABAMA_COUNTIES = {
"01001":"Autauga","01003":"Baldwin","01005":"Barbour","01007":"Bibb","01009":"Blount","01011":"Bullock","01013":"Butler","01015":"Calhoun","01017":"Chambers","01019":"Cherokee","01021":"Chilton","01023":"Choctaw","01025":"Clarke","01027":"Clay","01029":"Cleburne","01031":"Coffee","01033":"Colbert","01035":"Conecuh","01037":"Coosa","01039":"Covington","01041":"Crenshaw","01043":"Cullman","01045":"Dale","01047":"Dallas","01049":"DeKalb","01051":"Elmore","01053":"Escambia","01055":"Etowah","01057":"Fayette","01059":"Franklin","01061":"Geneva","01063":"Greene","01065":"Hale","01067":"Henry","01069":"Houston","01071":"Jackson","01073":"Jefferson","01075":"Lamar","01077":"Lauderdale","01079":"Lawrence","01081":"Lee","01083":"Limestone","01085":"Lowndes","01087":"Macon","01089":"Madison","01091":"Marengo","01093":"Marion","01095":"Marshall","01097":"Mobile","01099":"Monroe","01101":"Montgomery","01103":"Morgan","01105":"Perry","01107":"Pickens","01109":"Pike","01111":"Randolph","01113":"Russell","01115":"St. Clair","01117":"Shelby","01119":"Sumter","01121":"Talladega","01123":"Tallapoosa","01125":"Tuscaloosa","01127":"Walker","01129":"Washington","01131":"Wilcox","01133":"Winston"
}


def validate_alabama_counties():
    if len(ALABAMA_COUNTIES) != 67:
        raise ValueError("Alabama county index must contain exactly 67 counties")
    if any(len(fips) != 5 or not fips.startswith("01") or not fips.isdigit() for fips in ALABAMA_COUNTIES):
        raise ValueError("invalid Alabama county FIPS")
    if len(set(ALABAMA_COUNTIES.values())) != 67:
        raise ValueError("duplicate Alabama county name")
    return True
