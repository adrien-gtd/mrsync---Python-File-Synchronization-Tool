#!/Library/Frameworks/Python.framework/Versions/3.8/bin/python3
import argparse,os,sys

use ="""mrsync [OPTION]... SRC [SRC]... DEST

       mrsync [OPTION]... SRC [SRC]... [USER@]HOST:DEST

       mrsync [OPTION]... SRC [SRC]... [USER@]HOST::DEST

       mrsync [OPTION]... SRC

       mrsync [OPTION]... [USER@]HOST:SRC [DEST]

       mrsync [OPTION]... [USER@]HOST::SRC [DEST]"""



def dict_options():                                       #renvoie un dictionnaire {arg : [value]} à partir de la ligne de cmd 
    parser = argparse.ArgumentParser(usage=use)           #definit un objet 'ArgumentParser'
    parser.add_argument("path",help = "SRC [SRC]... [DEST]",nargs="+")                          #renvoie la liste des src / dest
    parser.add_argument("--list-only", help="list the files instead of copying them",action="store_true")   #option --list-only
    parser.add_argument("-r","--recursive", help="recurse into directories",action="store_true")            #option -r
    parser.add_argument("--size-only",help="skip files that match in size",action="store_true")             #option --size-only
    parser.add_argument("-I","--ignore-times",help="don't skip files that match size and time",action="store_true") #option -I
    parser.add_argument("--force",help="force deletion of dirs even if not empty",action="store_true")      #option --force
    parser.add_argument("--existing",help="skip creating new files on receiver",action="store_true")        #option --existing
    parser.add_argument("--ignore-existing",help="skip updating files that exist on receiver",action="store_true")  #option --ignore-existing
    parser.add_argument("--times","-t",help="preserve permissions",action="store_true") #option --times
    parser.add_argument("--perms","-p",help="preserve times",action="store_true")       #option --perms
    parser.add_argument("--delete",help="delete extraneous files from dest dirs",action="store_true")       #option --delete
    parser.add_argument("-a", "--archive",help="archive mode; same as -rpt (no -H)",action="store_true")    #option -a (-rpt)
    parser.add_argument("--server",help="shoudn't be used",action="store_true")       #Pour le ssh en mode push
    parser.add_argument("--pull",help="shouldn't be used",action = "store_true")      #pour le ssh en mode pull
    parser.add_argument("-v","--verbose",help="increase verbosity",action="count",default=0)        #option -v
    parser.add_argument("-q","--quiet",help="suppress non-error messages",action="store_true") #option -q
    parser.add_argument("--timeout",help="set I/O timeout in seconds",type=int) #option --timeout
    parser.add_argument("-u","--update",help="skip files that are newer on the receiver",action="store_true") #option -u
    parser.add_argument("-d","-dirs",help="transfer directories without recursing",action="store_true") #option -d
    parser.add_argument("--port",help="specify double-colon alternate port number",type=int) #option --port
    parser.parse_args()                

    args=parser.parse_args()            
    return vars(args)                   #revoie un dictionnaire contenant les options 


def list_option():              #transform le dictionnair en trois listes SRC,DEST,OPT
    dic = dict_options()
    SRC=format(dic.pop("path"))             #on met toutes les sources sous le meme format pour simplifier les algo suivants

    OPT=[]              #la suite du code n'est pas très lisible même pour moi qui l'ai codé mais on renvoie une liste des SRC, DEST, et OPT
    if dic["timeout"] != None:
        OPT.append("timeout")
        OPT.append(dic.pop("timeout"))
    if dic["port"] != None:
        OPT.append("port")
        OPT.append(dic.pop("port"))
    for key in dic:
        if key == "verbose":
            if dic[key] == 1:
                OPT.append("v")
            elif dic[key] >= 2:
                OPT.append("vv")
        elif dic[key]:
            OPT.append(key)

    if "archive" in OPT:                #--archive == -rpt
        if not "recursive" in OPT:
            OPT.append("recursive")
        if not "times" in OPT:
            OPT.append("times")
        if not "perms" in OPT:
            OPT.append("perms")
    
    lenSRC=len(SRC)     #si la liste des chemins passé en arg est > 1, alors le dernier est la DEST et les autres sont les sources
    if lenSRC > 1:      
        DEST = [SRC.pop()]          #on fait attention au cas ou la dest est en mode ssh ou deamon dans ce cas, on effectue le programme adéquat en mode push
        if "::" in DEST[0]:
            OPT.append("deamon_push")       
        elif ":" in DEST[0]:
            OPT.append("ssh")
    else:                       #si le nombre de chemins passé en arg est égale a 1, on effectue le programme en mode list-only 
        if "list_only" not in OPT:
            OPT.append("list_only")
        DEST=[]

    for path in SRC:                #verifie si la SRC est en local ou en distant, lève une erreur en cas de mauvaise utilisation
        if "::" in path:
            if lenSRC > 2 or "ssh" in OPT or "deamon_push" in OPT:
                print("ERROR",use,sep='\n',file = sys.stderr)
                sys.exit(1)
            OPT.append("deamon_pull")
        elif ":" in path:
            if lenSRC > 2 or "ssh" in OPT or "deamon_push" in OPT:
                print("ERROR",use,sep='\n',file = sys.stderr)
                sys.exit(1)
            OPT.append("ssh_pull")
    
    return (SRC,DEST,OPT) #on renvoie la liste des SRC, la dest et les option

def format(SRC):               #on remplace les éléments de SRC par leur chemin absolue (en gardant le / a la fin s'il y en a un) pour ne pas avoir d'erreur en cas de changement de repertoire plus loin
    slash = False
    for index in range(len(SRC)):
        if ":" in SRC[index]:
            continue
        
        if SRC[index][-1] =='/' or SRC[index][-1] == ".":
            slash = True

        if "change" in SRC:     #le seul cas est quand on a appelé mrsync en mode ssh  sans preciser de path (user@host:) le programme gere ce cas plus tard
            break

        SRC[index] = os.path.abspath(SRC[index])

        if slash:
            SRC[index]+="/"
        
        slash = False

    return SRC

use_deamon = "--deamon option used to start-up the deamon server on the remote host"

def deamon():           #parser pour le mode serveur --deamon 
    parser = argparse.ArgumentParser(usage=use_deamon)
    parser.add_argument("--deamon",help="run as an mrsync daemon",action="store_true")
    parser.add_argument("--address",help="bind to the specified address")
    parser.add_argument("--no-detach",help="do not detach from the parent",action="store_true")
    parser.add_argument("--port",help="listen on alternate port number")

    args = parser.parse_args()
    OPT = ["deamon"]
    if args.address:
        addr_ = args.address
    else:
        addr_ = "localhost"
    if args.port:
        port_ = args.port
    else:
        port_ = 10873
    OPT.append((addr_,port_))
    if args.no_detach:
        OPT.append("no_detach")
    return OPT #renvoie la liste des option passé en argument de la fonction avec le couple (addr, port) par defaut (localhost, 10873) ou en fonction des options
