import filelist,sys,os,message,signal,hashlib

MAXEBYTE = 40000 #peut etre modifier

def client(SRC,OPT,wfd,rfd): #s'occupe de la source 

    file_list = filelist.file_list(SRC,OPT)          #on crée la liste de fichiers
    if ("list_only" in OPT) & (not "pull" in OPT):                #l'option --list-only est activée
        filelist.display(file_list,OPT,wfd)
        if "deamon_pull" in OPT: #dans le cas du demon en mode pull, on ne peut pas print, il faut donc envoyer les resultats sur la pipe (géré dans filelist)
            return #on pass pour fermer correctement la socket
        sys.exit(0) 


    message.send(wfd,1,file_list,OPT) #on envoie la liste des fichier de source au receveur pour le génerateur
    

    (tag,request) = message.receive(rfd,OPT)                #on reçois les requettes du génerateur, request : (path,file_name)

    while tag != 3: #tag 3 = fin du generateur
        if tag == 2:            #envoie d'un fichier
            try:
                fd = os.open(os.path.join(request[0],request[1]),os.O_RDONLY)
                message.send(wfd,4,request[1],OPT)
                buff = os.read(fd,MAXEBYTE)
                while len(buff) > 0:
                    message.send(wfd,5,buff,OPT)
                    buff = os.read(fd, MAXEBYTE)
                message.send(wfd,6,"end",OPT)
            except FileNotFoundError: #Le fichier n'est pas dans la source (en general ne s'active jamais)
                if ("vv" in OPT) & (not "quiet" in OPT):
                    message.print_log(f"Error, couldn't open {request}, passing!")
            except BrokenPipeError: #La pipe c'est cassé, en general ne s'active pas non plus
                if not "quiet" in OPT:
                    message.print_log(f"Erreur : borken pipe, impossible de continué, fichier : {request}")

        elif tag == 7:          #nouveau dossier
            message.send(wfd,8,request,OPT)
        
        elif tag == 10:         #demande de supprimer le fichier / dossier
            message.send(wfd,10,request,OPT)
        

        elif tag == 11:         #update
            os.chdir(request[0])
            message.send(wfd,11,request[1],OPT)
            update(rfd,wfd,request[1],OPT)




 
        (tag,request) = message.receive(rfd,OPT) #on boucle
    
    message.send(wfd,9,"fin",OPT) #on envoie au receveur que c'est la fin des demandes 
        

#Fonctionnement inverse de la fonction update du module receveur, cf ce derniers pour plus d'explications.


def update(rfd,wfd,name,OPT):
    fd = os.open(name, os.O_RDONLY)
    (tag,(taille,hash)) = message.receive(rfd,OPT)
    while tag != 15:
        data = os.read(fd,taille)
        if len(data) == 0:
            message.send(wfd,15,"",OPT)
            break
        correct_hash = hashlib.md5(data)
        if correct_hash.digest() == hash:
            message.send(wfd,13,"",OPT)

        else:
            message.send(wfd,14,(len(data),data),OPT)
        
        (tag,(taille,hash)) = message.receive(rfd,OPT)
    if tag == 15:
        data = os.read(fd,os.path.getsize(name))
        message.send(wfd,15,data,OPT)
    os.close(fd)



    
