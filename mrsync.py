#!/Library/Frameworks/Python.framework/Versions/3.8/bin/python3

#Adrien Guittard

import option,sender,filelist,os,server,receiver,sys,signal,time,message,deamon

def update_OPT(OPT):                #argparse transforme les - en _ par exemple --list-only devient list_only 
    for i in range(len(OPT)):
        if OPT[i] == "v" or OPT[i] == "vv":
            OPT[i] = "-" + OPT[i]
        else:
            if "_" in OPT[i]:
                OPT[i] = OPT[i].replace("_","-")
            OPT[i] = "--" + OPT[i]
    return OPT          #return la liste OPT qui est acceptable par le programme


def local_(SRC,DEST,OPT):  #si mrync est appelé en mode local
    rfd1,wfd1 = os.pipe()
    rfd2,wfd2 = os.pipe()
    pid = os.fork()


    if pid == 0:            #fils qui devient le sender
        os.close(rfd1)
        os.close(wfd2)
        sender.client(SRC,OPT,wfd1,rfd2)
        sys.exit(0)

    else:                   #pere qui devient le receveur
        os.close(wfd1)
        os.close(rfd2)
        os.dup2(wfd2,1)
        os.dup2(rfd1,0)
        os.close(wfd2)
        os.close(rfd1)          #redirige les entrées sortis de la pipe vers les stdin et stdout
        server.server(DEST,OPT)
        os.wait()       #attend le fils avant de finir
        sys.exit(0)

def ssh_path(ssh_adress):       #découpage d'un sting de la forme "user@host:path" et renvoie (user,host,path)
    point_index = ssh_adress.index(":")
    if '@' in ssh_adress:
        at_index = ssh_adress.index('@')
        user = ssh_adress[:at_index]
        host = ssh_adress[at_index+1:point_index]
    else:
        user = ""
        host = ssh_adress[:point_index]
    path = ssh_adress[point_index+1:]
    return (user,host,path)


def ssh_push(SRC,user,host,path,OPT):       #ssh en mode push (coté local)
    rfd1,wfd1 = os.pipe()
    rfd2,wfd2 = os.pipe()
    pid = os.fork()

    if pid == 0:            #le fils va executer le programme mrsync sur le shell distant via un canal ssh
        os.close(wfd1)
        os.close(rfd2)
        os.dup2(wfd2,1)
        os.dup2(rfd1,0)     #redirige les sorties vers les tubes
        argv = ["ssh", "-e","none"]
        if user != "":
            argv += ["-l",user]
        OPT = update_OPT(OPT)
        argv += [host,"--","./mrsync.py","--server"] + OPT + [path]     #on appelle le programme sur le shell distant en ajoutant l'option --serveur
        os.execvp("ssh",argv)

    else:                   #le père est l'envoyeur, côté source du coup
        os.close(rfd1)
        os.close(wfd2)
        sender.client(SRC,OPT,wfd1,rfd2)
        os.wait()
        sys.exit(0)


def ssh_pull(user,host,path,OPT,SRC,DEST):      #ssh en mode pull (DEST distante et SRC local)
    if (len(DEST) == 0) or ("list_only" in OPT):        # pas de DEST : on affiche simplement le contenu de SRC, pas besoin de rediriger les sorties standards, execvp ecris directement sur la bonne sortie
        if path == "": 
            path = "change"
        argv = ["ssh", "-e","none"]
        if user != "":
            argv += ["-l",user]
        argv += [host,"--","./mrsync.py", path]
        os.execvp("ssh",argv)
    
    rfd1,wfd1 = os.pipe()
    rfd2,wfd2 = os.pipe()
    pid = os.fork()

    if pid == 0:            #le fils va devenir l'envoyeur coté distant
        os.close(wfd1)
        os.close(rfd2)
        os.dup2(wfd2,1)
        os.dup2(rfd1,0)
        argv = ["ssh", "-e","none"]
        if user != "":
            argv += ["-l",user]
        OPT = update_OPT(OPT) 
        argv += [host,"--","./mrsync.py"] + OPT + ["--pull",path]  #on appelle le programme sur l'autre shell avec l'option --pull pour qu'il sache son rôle
        os.execvp("ssh",argv)  

    else:                   #le pere devient le receveur, pas besoin de rediriger les sorties 
        os.close(rfd1)
        os.close(wfd2)
        receiver.receiver(DEST,OPT,wfd1,rfd2)
        sys.exit(0)
        


if __name__ == "__main__":
    try:                #Pour ratrappé les erreur d'execution qui ne sont pas deja ratrapé dans le programme
        if sys.argv[1] == "--deamon":   #mode deamon sereur
            OPT = option.deamon()
            deamon.deamon_server(OPT[1],OPT)
        SRC,DEST,OPT = option.list_option()

        if "pull" in OPT:       #mode ssh en pull côté remote
            sender.client(SRC,OPT,1,0)
            sys.exit(0)
        if "ssh_pull" in OPT:       #mode ssh en pull côté local
            OPT.remove("ssh_pull")
            (user,host,path) = ssh_path(SRC[0])
            ssh_pull(user,host,path,OPT,SRC,DEST)
            sys.exit(0)

        if "server" in OPT:         #ssh en mode push côté remote
            server.server(SRC,OPT)
            sys.exit(0)
        if "ssh" in OPT:                #ssh en mode push côté local
            OPT.remove("ssh")
            (user,host,path) = ssh_path(DEST[0])
            ssh_push(SRC,user,host,path,OPT)
            sys.exit(0)

        if ("deamon_pull" in OPT) or ("deamon_push" in OPT): #mode deamon côté local (push ou pull)
            if "deamon_push" in OPT:
                (_,host,path) = ssh_path(DEST[0])       #decoupe l'argument passer en ligne d'appelle 
                path = path.replace(":","")
                if path == "":
                    path = "/"
                DEST[0] = path
            else:
                (_,host,path) = ssh_path(SRC[0])
                path = path.replace(":","")
                if path == "":
                    path = "/"
                SRC[0] = path
            if "port" in OPT:
                port_index = OPT.index("port")+1
                port = OPT[port_index]
            else:
                port = 10873
            deamon.deamon(SRC,DEST,OPT,host,port)       #lance le client deamon, il gere lui le mode pull ou push 
            sys.exit(0)

        if "list_only" in OPT:          #local en mode list only (pas besoin de receveur)
            if SRC == ["change"]:
                SRC = [os.path.curdir + "/"]
            sender.client(SRC,OPT,1,0)  #on utilise pas les arguments wfd et rfd de sender.client
        local_(SRC,DEST,OPT)
    except ConnectionResetError:
        message.print_log("Error socket")
        sys.exit(10)
    except KeyboardInterrupt:
        message.print_log("Recived sigint")
        sys.exit(20)
    except EOFError:
        message.print_log("Erreur data stream")
        sys.exit(12)