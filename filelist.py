#!/Library/Frameworks/Python.framework/Versions/3.8/bin/python3
import os,time,stat,sys,message

def file_list(SRC,OPT): #renvoie la list des fichiers de SRC (qui peut etre une liste) sous la forme [(abs path, nom du fichier en fonction de SRC, {mode,mtime, size})]
    SRC = slash(SRC,OPT) 
    if "recursive" not in OPT:
        files = basic_list(SRC)
    else:
        files = rec_list(SRC)


    return info_list(files)


def slash(SRC,OPT):                         #si path dans SRC finit par un slash on le remplace par les lien a l'interieur du dossier           
    if len(SRC) == 0:
        return []
    
    path = SRC[0]
    if path[-1] == "/":
        try:                            #si path est un fichier, on ne peut pas l'ouvrir avec os.listdir(), on l'enleve de src
            files=[]
            for f in os.listdir(path):
                files.append(os.path.join(os.path.abspath(path),f))
            return  slash(SRC[1:],OPT) + files
        except:
            if ("vv" in OPT) & (not "quiet" in OPT):
                message.print_log(f"Error : {path} is not a directory, passing")
            return slash(SRC[1:],OPT)
    return SRC[:1] + slash(SRC[1:],OPT)
    

def rec_list(SRC):        #si l'option -r est active, on ouvre les répertoires récursivement en gardant la le chemin pour chaque repertoires
    files = []            #output : [(path,[list of files])] (path sera utile si plusieurs sources sont mises en entrée)

    for path in SRC:
        files_rec = []
        files_rec.append(os.path.basename(path))

        if os.path.isdir(path):
            os.chdir(path + "/../")
            files_rec += open_rec(os.path.basename(path))
        files.append((os.path.abspath(path+"/../"),files_rec))
    return files
                
def open_rec(path):         #sous-fonction de la fonction rec_list
    files = []
    for f in os.listdir(path):
        path_ = os.path.join(path,f)
        files.append(path_)
        if os.path.isdir(path_):
            files += open_rec(path_)
    return files
    

def basic_list(SRC):                #renvoie simplement la liste [(path,[file]),....]
    files=[]   
    
    for path in SRC:
        files.append((os.path.abspath(path + "/../"),[os.path.basename(path)]))

    return files



def info_list(file):                 #créer un dictionnaire associant à chaque fichiers de la liste 'file' son 'mode', date de modif, taille 
    info = []
    for tuple in file:
        os.chdir(tuple[0])
        for f in tuple[1]:
            s = os.stat(f)
            size = s.st_size
            mode = s.st_mode
            t = s.st_mtime
            info.append((tuple[0],f,{
                "size":size,
                "mode":mode,
                "time":t,
            }))
    return info

def display(info,OPT,wfd): #gere l'affiche de la fonction list-only
    info.sort()
    for item in info:
        mode = item[2]["mode"]
        t = item[2]['time']
        size = item[2]["size"]
        if "deamon_pull" in OPT:
            message.send(wfd,18,"{:<10} {:>11} {:<19} {}".format(stat.filemode(mode),size,time.strftime("%Y/%m/%d %H:%M:%S",time.localtime(t)),item[1]),OPT)
        else:
            print("{:<10} {:>11} {:<19} {}".format(stat.filemode(mode),size,time.strftime("%Y/%m/%d %H:%M:%S",time.localtime(t)),item[1]))
