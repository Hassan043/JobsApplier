"""User-requested source inventory. Catalog entries do not imply working connectors."""
import re
import unicodedata

GROUPS={
 'accounts':'LinkedIn;GitHub;Fiverr;Upwork;Freelancer;Indeed;Dice;Google',
 'talent_networks':'Arc;Turing;Andela;Lemon.io;Proxify;G2i;Crossover;Gun.io;Toptal',
 'ai_contract':'micro1;Mercor;Askable',
 'remote_boards':'Wellfound;Himalayas;Y Combinator jobs;We Work Remotely;Remotive;Remote OK;Remote Rocketship;Jobicy;NoDesk;Jobgether;Working Nomads;Jobspresso;Dynamite Jobs;Remote Front;FlexJobs;Hacker News jobs;aijobs.net;Python.org jobs;Built In;Glassdoor;ZipRecruiter',
 'relocation':'Relocate.me;VisaSponsor.jobs;Arbeitnow;Landing.jobs;EURES;No Fluff Jobs;Just Join IT;Welcome to the Jungle',
 'pakistan':'Rozee.pk;Mustakbil;Indeed Pakistan',
 'employer_feeds':'Greenhouse;Lever;Pangian;Remote.co',
}
COUNTRIES={
 'DE':'Make it in Germany;Jobborse (Germany);StepStone;Xing Jobs;Berlin Startup Jobs;Jobware;Absolventa',
 'NL':'Werk.nl;Nationale Vacaturebank;Monsterboard;Together Abroad;Undutchables',
 'BE':'VDAB;Le Forem;Actiris;StepStone BE;Jobat;BrusselsJobs',
 'LU':'ADEM;Jobs.lu;Moovijob',
 'IE':'JobsIreland;IrishJobs;Jobs.ie;GradIreland',
 'FR':'France Travail;Apec;HelloWork;ChooseYourBoss;LesJeudis',
 'ES':'SEPE;Empleate;InfoJobs;Infoempleo;Tecnoempleo;ThinkSpain Jobs',
 'PT':'IEFP;Net-Empregos;Sapo Emprego;ITJobs',
 'IT':'ANPAL;Lavoro.gov;InfoJobs IT;Corriere Lavoro;Motore Lavoro;Jobrapido IT;Subito Lavoro',
 'AT':'AMS;Karriere.at;StepStone AT;derStandard Jobs',
 'CH':'Job-Room;Jobs.ch;Jobup.ch;Indeed CH;Jobs.nzz.ch',
 'PL':'Public Employment (Poland);Pracuj.pl;Bulldogjob;RocketJobs',
 'DK':'Jobnet;Work in Denmark;Jobindex;Ofir;TheHub',
 'SE':'Arbetsformedlingen;Sweden.se;Blocket Jobb;Monster SE',
 'NO':'NAV Arbeid;Work in Norway;Finn.no Jobb;Jobbnorge;Arbeidsplassen',
 'FI':'Job Market Finland;Work in Finland;Duunitori;Monster FI;Oikotie Tyopaikat',
 'MC':'Monaco Economic Board',
 'US':'Dice;Built In;USAJOBS',
 'CA':'Job Bank;Immigration info (Canada);Workopolis;Monster CA;BC Jobs;Jobillico;Eluta',
 'AU':'Workforce Australia;SEEK;CareerOne;APS Jobs;EthicalJobs',
 'NZ':'Careers.govt.nz;Immigration NZ;SEEK NZ;Trade Me Jobs',
 'JP':'Daijob;GaijinPot Jobs;CareerCross;Wantedly',
 'HK':'JobsDB HK;CT Good Jobs;Recruit.com.hk',
 'TW':'104 Job Bank;1111;CakeResume;Yourator',
 'SG':'MyCareersFuture;JobStreet',
 'CN':'Liepin;Boss Zhipin;51Job',
 'MIDDLE_EAST':'Bayt;GulfTalent;Naukrigulf;Dubizzle Jobs;Gulf News Jobs;Jadarat',
}
ALIASES={
 'Jobborse (Germany)':['Jobborse','Jobbörse'], 'Empleate':['Empléate'],
 'Arbetsformedlingen':['Arbetsförmedlingen'],'Oikotie Tyopaikat':['Oikotie Työpaikat'],
 'Welcome to the Jungle':['Otta'],'FlexJobs':['FlexJobs (paid)'],
 'Public Employment (Poland)':['Public Employment'], 'Immigration info (Canada)':['Immigration info']}
INFORMATION={'Immigration info (Canada)','Immigration NZ','Sweden.se','Monaco Economic Board','Careers.govt.nz'}
DOCUMENTED={
 'Remotive':('live_smoke_verified','public_feed','https://github.com/remotive-com/remote-jobs-api','Public feed cached for six hours; attribution retained. Live smoke check returned 3 valid postings on 2026-11-06; no eligibility verification.'),
 'Arbeitnow':('live_smoke_verified','public_feed','https://www.arbeitnow.com/blog/job-board-api','Bounded first page; remote is not worldwide eligibility. Live smoke check returned 3 valid postings on 2026-11-06; no eligibility verification.'),
 'Greenhouse':('live_smoke_verified','employer_board','https://docs.greenhouse.io/job-board','Explicit employer token required; one board smoke-tested 2026-11-05.'),
 'Lever':('fixture_tested','employer_board','https://github.com/lever/postings-api','Explicit employer site identifier; first 100 postings only.'),
 'Himalayas':('documented_not_implemented','public_api_research','https://himalayas.app/api','Documented API; apply-link/source/expiry requirements must be implemented before use.'),
 'LinkedIn':('manual_only','manual_import','https://www.linkedin.com/help/linkedin/answer/a1341387/prohibition-of-scraping-software','Use manual review or a separately approved integration; no login scraping or automation adapter.'),
 'Pangian':('degraded','legacy_compatible_feed','','Last live probe returned non-JSON; not a healthy source.'),
 'FlexJobs':('legacy_unverified','manual_import','','Historical account scraper is excluded from clean portfolio; no current live adapter.'),
 'Remote.co':('legacy_unverified','manual_import','','Historical account scraper is local-only; no current live adapter.'),
 'Bayt':('legacy_unverified','manual_import','','Historical scraper is local-only; current collection route unverified.'),
}


def slug(name):
    text=unicodedata.normalize('NFKD',name).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','-',text).strip('-')


def portal_catalog():
    entries={}
    def add(name,group,country=None):
        ident=slug(name)
        if ident not in entries:
            status,access,reference,note=DOCUMENTED.get(name,('research_required','manual_import','',
                'Site identity, current access method, authentication, terms, and export availability are unverified. Generic normalized import is available; no native connector is claimed.'))
            if name in INFORMATION:
                status,access,note='reference_only','information','Reference/information resource; not asserted to be a current vacancy feed.'
            if name in {'GitHub','Google'}:
                status,access,note='discovery_only','manual_discovery','Discovery/account platform, not a native job feed. Use employer links or normalized manual imports.'
            entries[ident]={'id':ident,'name':name,'aliases':ALIASES.get(name,[]),'groups':[], 'countries':[],
                'status':status,'access':access,'reference':reference,'note':note,
                'authentication':'none_for_implemented_public_GET' if status in {'fixture_tested','live_smoke_verified'} else 'unverified_or_not_applicable'}
        row=entries[ident]
        if group not in row['groups']:row['groups'].append(group)
        if country and country not in row['countries']:row['countries'].append(country)
    for group,names in GROUPS.items():
        for name in names.split(';'):add(name,group,'PK' if group=='pakistan' else None)
    for country,names in COUNTRIES.items():
        for name in names.split(';'):add(name,'country_boards',country)
    return sorted(entries.values(),key=lambda r:r['name'].casefold())


def select_portals(group=None,country=None,status=None):
    if group and group not in set(GROUPS)|{'country_boards'}:raise ValueError('Unknown portal group')
    return [row for row in portal_catalog() if (not group or group in row['groups']) and
            (not country or country.upper() in row['countries']) and (not status or row['status']==status)]
