import message,os,sys,socket,sender,receiver,signal

def deamon(SRC,DEST,OPT,host,port):     #client en mode deamon
    clisock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        clisock.connect((host,port))
    except ConnectionRefusedError:      #Erreur de connexion au serveur
        if not "quiet" in OPT:
            message.print_log("Erreur de connection socket, verify host and port")
        sys.exit(1)

    if "deamon_push" in OPT:            #mode push
        message.send(clisock.fileno(),16,(DEST,OPT),OPT) #on envoie au serveur le tag 16 pour qu'il sache quel est son rôle
        sender.client(SRC,OPT,clisock.fileno(),clisock.fileno()) #le processus devient l'envoyeur (car la source est côté local)
        clisock.close() #on ferme la socket avant de terminer le processus
        sys.exit(0)
    else:                               #mode pull
        message.send(clisock.fileno(),17,(SRC,OPT),OPT) #pareil, on envoie un message au server deamon pour qu'il connaisse sont role
        if "list_only" in OPT:          #mode pull avec l'option list-only, permet d'afficher correctement les messages recus
            while True:             #mode de reception syncrone, le server deamon envoie les fichier avec les informations un par un, il suffit de les print 
                try:
                    (_,mess) = message.receive(clisock.fileno(),OPT)
                    print(mess)
                except EOFError:        #la socket a été fermer côté serveur, fin de la requete, on ferme la socket et termine le processus
                    clisock.close()
                    sys.exit(0)
        receiver.receiver(DEST,OPT,clisock.fileno(),clisock.fileno())   #mode pull 'normal' (sans list-only)
        clisock.close()
        sys.exit(0)

def deamon_server(addr,OPT):        #lance le serveur du mode deamon
    try:        #pour verifier qu'il n'y a pas déjà un server sur cette adresse
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(addr)      #si on peut se connecter, c'est qu'il y a deja un serveur sur cette adresse
        message.print_log("Error, can't start a seconde server on the same port / address : exiting!")
        sys.exit(1)
    except:                         #sinon, on lance le serveur
        pass


    if not "no_detach" in OPT:      #de base, le server se détache du shell, c'est a dire, le fils lance le server et le pere se termine
        p = os.fork()
        if p != 0:
            print("Detaching from shell, deamon process pid :",p)
            sys.exit(0)
        
    fd = os.open("log",os.O_WRONLY | os.O_CREAT | os.O_TRUNC)           #créer un fichier pour les log dans le meme repertoire que mrsync.py qui sera reset a chaque utilisation (pour le lire j'utilise : ssh user@host cat log) 
    os.dup2(fd,2)
    os.close(fd)        #on redirige la sortie d'erreur sur ce fichier comme ca tous les message d'erreur seront écrits dans ce fichier


    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #creation du serveur
    serversocket.bind(addr)
    serversocket.listen()
    active_child = []                   #garde une liste de tous les fils actifs
    def sigchild(sig,frame):            #quand un fils se termine on l'enlève de la liste 
        p,_ = os.wait()
        try:
            active_child.remove(p)
        except ValueError:          #un generateur vient de fini, on ne fait rien
            pass                

    def sigterm(sig,frame):             #quand on recoit le signal sigterm, on envoie le signal sigusr2 (sigusr1 est deja utilisé pour le generateur) aux fils encore en vie pour qu'ils ferment correctement leur socket client
        for child in active_child:
            os.kill(child,signal.SIGUSR2)
        serversocket.close
        sys.exit(20)

    def sigusr2(sig,frame):             #ferme correctement les sockets des fils encore en cours d'execution si le serveur recoit le signal sigterm
        clientsocket.close()
        sys.exit(0)

    
    signal.signal(signal.SIGCHLD,sigchild)
    signal.signal(signal.SIGTERM,sigterm)

    while True:
        (clientsocket,_) = serversocket.accept()
        pid = os.fork()     #à chaque nouvelle connexion, on créer un nouveau fils qui execute la requete du client

        if pid == 0:                            
            os.lseek(2,0,os.SEEK_END)           #pour les message d'erreur, a chaque nouveau fils on place le curseur a la fin du fichier log (si un nouveau fils s'execute en même temps, 
#                                                cette solution ne marchera pas, si mrsync est utilisé pour un sit web par exemple, il faudrait revoir le systeme de log en mode deamon 
#                                                mais dans le cadre du projet je ne pesne pas que cela pose problème)
            signal.signal(signal.SIGUSR2,sigusr2)
            (tag,(liste,OPT)) = message.receive(clientsocket.fileno(),OPT) #on recoit le message évoqué plus haut, on sait donc quel est le rôle du serveur
            if tag == 16:               #mode push
                receiver.receiver(liste,OPT,clientsocket.fileno(),clientsocket.fileno())
                clientsocket.close()
                sys.exit(0)
            elif tag == 17:             #mode pull
                if liste == ["/"]:
                    liste = [os.path.curdir + "/"]
                sender.client(liste,OPT,clientsocket.fileno(),clientsocket.fileno())
                clientsocket.close()
                sys.exit(0)

        else:
            active_child.append(pid) #on ajoute le fils a la liste des processus actif
            clientsocket.close() #on ferme la socket chez le père