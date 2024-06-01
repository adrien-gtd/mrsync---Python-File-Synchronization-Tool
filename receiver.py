import os,sys,message,filelist,generator,signal,time,hashlib,shutil

def receiver(DEST,OPT,wfd,rfd): #programme côté destination
    file_list_DEST = filelist.file_list(DEST,OPT) # on recupere la liste contenant les info de DEST (=repertoire de destionation)
    os.chdir(DEST[0])                   #on se met dans repertoir DEST 
    (tag,file_list_SRC) = message.receive(rfd,OPT) #on recoit la liste des fichier de source

    pid = os.fork()                 #en mode ssh le message juste en dessous s'affiche 2 fois si le os.fork est après et après avoir chercher pendant 40 min je ne vois toujours pas pourquoi
#                                    j'ai l'impression que le processus père recommence l'appelle de fonction depuis le début mais en mettant le os.fork avant pas d'erreur d'affichage et le
#                                    le rest semble marcher correctement.

    if (tag == 1) & pid != 0:  
        if (("v" in OPT) or ("vv" in OPT)) & (not "quiet" in OPT): #print que la liste a été recu si verbose est actif
            message.print_log("Liste bien reçu")

    if pid == 0: 
        generator.generator(file_list_SRC,file_list_DEST,OPT,pid,rfd,wfd)       #on fork le générateur


    else:         #le père recoit les requetes du sender elles-même recus du generateur
        (tag,name) = message.receive(rfd,OPT)
        while tag != 9:  #tag 9 = fin de transimition des fichiers 
            if (tag != 4) & (tag != 8) & (tag != 10) & (tag != 11):       #pour être sûr de ne pas recevoir le mauvais message, normalement n'arrive jamais                     
                message.print_log("Erreur dans la récéption du fichier, mauvais tag! " + str(tag) + " " + name)
                sys.exit(12)

            if tag == 4:                                #copie un fichier entier depuis la source
                fd = os.open(name,os.O_WRONLY | os.O_CREAT)
                (tag,data) = message.receive(rfd,OPT)
                while tag != 6:      #au cas ou le fichier ne s'est pas envoyé en une fois, le sender lis les fichiers par blocks de 40 000 bytes normalement plus petit que le buffer de la pipe 
                    os.write(fd,data)#donc normalement pas d'interblocage, si cela arrive on il faut changer la valeur de MAXBYTE du fichier sender ligne 3
                    (tag,data) = message.receive(rfd,OPT)

            if tag == 8:                                #demande de création de dossier 
                try:
                    os.mkdir(name)
                except FileExistsError:         #le dossier existe déja
                    pass
            
            if tag == 10:                               #demande de supression du fichier (--delete)
                try:
                    os.unlink(name)
                except PermissionError:    #name est un dossier
                    try:
                        os.rmdir(name)
                    except OSError:         #le dossier est plein
                        shutil.rmtree(name)
                except FileNotFoundError:   #name n'est pas dans DEST
                    if ("vv" in OPT) & (not "quiet" in OPT):
                        message.print_log(f"Erreur : {name} n'est pas dans DEST!")
            
            if tag == 11: #demande d'update un fichier
                update(name,rfd,wfd,pid,OPT)

            (tag,name) = message.receive(rfd,OPT) #on boucle

    if ("perms" in OPT) or ("times" in OPT): #on verifie s'il y'a besoin de modifier la protection ou le temps de derniere modif des fichier (options --perms et --times)
        for info in file_list_SRC:
            try:  #car en fonction des options, tous les fichiers dans less sources ne sont pas forcément dans DEST 
                name = info[1]
                if "perms" in OPT:
                    mode = info[2]["mode"]
                    os.chmod(name,mode)
                
                if "time" in OPT:
                    time = info[2]["time"]
                    os.utime(name,times=(time,time))
            except:
                pass
    

"""
Principe de la fonction update :
Le but est de ne pas systématiquement envoyer l'intégralité du fichier à travers le réseau.
Sur des petits fichiers, cet algorithme est peu efficace car on envoie quasiment autant de messages que si on devait envoyer le fichier en entier.
Mais ce n'est pas grave car ces fichiers n'encombrent pas la bande passante.
Pour des fichiers plus gros, on procède comme suit : d'abord, on découpe le fichier de destination en plusieurs blocs (ici 5, on peut changer cette valeur).
On crée le hash de chaque partie du fichier que l'on envoie à l'expéditeur (qui se trouve du côté source).
Ce dernier va comparer le hash du destinataire et le hash du bloc de même taille du côté source.
S'ils correspondent, on n'envoie rien, sinon on envoie le bon bout de fichier.
Du côté du destinataire, on crée le même fichier que dans la source dans un fichier temporaire qui va remplacer le fichier à mettre à jour dans la destination.
Ne pas oublier que le générateur est en pause pendant les mises à jour de fichier car il communique sur les mêmes pipes que le sender et le receiver.
On envoie donc le signal SIGUSR2 à ce dernier pour lui signaler la fin de la mise à jour.
"""


def update(name,rfd,wfd,pid,OPT): 
    
    fd = os.open(name,os.O_RDWR) #on ouvre le fichier dans DEST 
    temp_fd = os.open("fichiertemp",os.O_RDWR | os.O_CREAT | os.O_TRUNC) #on ouvre un fichier temporaire 

    taille_block = os.path.getsize(name) // 5 #on divise le fichier en 5 (si la taille du fichier est divisible par 5) ou 6
    if taille_block < 100: #si la taille du fichier est < 100 byte on ne le découpe pas
        taille_block = os.path.getsize(name)

    block = os.read(fd,taille_block)
    while len(block) > 0:
        hash = hashlib.md5(block) #on créer le hash du block
        message.send(wfd,12,(len(block),hash.digest()),OPT) #on l'envoie a l'envoyeur
        (tag,resp) = message.receive(rfd,OPT) #on recoit sa réponse
        if tag == 14: #soit c'est le mauvais hash 
            os.write(temp_fd,resp[1]) # on ecrit dans le fichier temporaire le bon bout de fichier
        elif tag == 13: #soit c'est le bon 
            os.write(temp_fd,block) #on écrit le meme block dans le fichier temp
        elif tag == 15: #c'est la fin de fichier côté sender
            break
        block = os.read(fd,taille_block) #on boucle

    if len(block) == 0: #Si on est arrivé a la fin de fichier côté dest 
        message.send(wfd,15,("",""),OPT) #on envoie un mess a sender 
        (tag,data) = message.receive(rfd,OPT) #il envoie la fin du fichier 
        os.write(temp_fd,data) #on écrit la fin dans le fichier temp

    os.close(fd) #on ferme le file descriptor du fichier a mettre a jour
    os.unlink(name) #on le supprime 
    fd = os.open(name,os.O_WRONLY | os.O_CREAT) #on le recréer 
    os.lseek(temp_fd,0,os.SEEK_SET) #on se place au début du fichier temporaire
    file = os.read(temp_fd,os.path.getsize("fichiertemp")) #on ecrit tout dans le nouveau fichier 
    os.write(fd, file)
    os.close(temp_fd) #on ferme le fd du fichier temp
    os.unlink("fichiertemp") #on le supprime
    os.close(fd) #on ferme le fd du 
    os.kill(pid,signal.SIGUSR2) #reprise du generateur

