import sys,os,message,stat,signal
from random import randint
 
def handler(sig,frame): #en cas d'update, le receveur et le sender communiquent, pour ne pas mélanger tous les messages, le generateur attend la fin de leur communication
    pass

#le code de la fonction qui suit n'est pas très lisible et par manque de temps je n'ai pas pu revenir dessus pour la rendre correcte a lire, mais elle fonctionne

def generator(files_SRC,files_DEST,OPT,pid,rfd,wfd):    #fonction qui compare les 2 listes de fichiers et decide que faire en fonction des options
    files_SRC = quicksort(files_SRC)        #trie des 2 listes en fonction des noms relatifs (donc le deuxieme élément de la liste)
    files_DEST = quicksort(files_DEST)

    signal.signal(signal.SIGUSR2,handler) #signal évoqué plus haut 

    if "delete" in OPT:                     #comme les 2 listes sont trié, on peut parcourir les 2 liste en temps linéaire, pas besoin d'utiliser 2 boucle for
        i=0 ; j=0
        while (i < len(files_SRC)) & (j < len(files_DEST)):         
            SRCfile = files_SRC[i][1]
            DESTfile = files_DEST[j][1]
            if SRCfile == DESTfile: # si le fichier est présent dans les 2 listes on avance de 1 dans les 2 listes
                j+=1;i+=1
            elif SRCfile < DESTfile: #si le nom du fichier de la liste SRC est plus petit, il n'est pas dans DEST, on avance de 1 dans SRC
                i+=1
            elif SRCfile > DESTfile: #si le nom du fichier dans la liste SRC est plus grand, alors le fichier de la liste DEST n'est pas dans SRC, on le suppr
                message.send(wfd,10,DESTfile,OPT)
                j+=1
        if i+1 == len(files_SRC): #si on est arrivé a la fin de SRC, il faut supprimer le reste des fichiers de DEST (qui ne sont du coup pas dans SRC)
            while j < len(files_DEST):
                DESTfile = files_DEST[j][1]
                message.send(wfd,10,DESTfile,OPT)
                j+=1



    for info in files_SRC: #J'aurais du faire comme pour delete et parcourir les listes en temps lineaire plutot que de faire 2 boucles for
        file = info[1] #cette boucle n'est pas très lisible, et le nom des variable n'est pas forcément évident mais une fois encore, je n'ai pas eu le temps de rectifier cela
        is_file = True
        done = False #dans la 2 boucle ci-dessous, par défault on demande a l'envoyeur d'envoyer le fichier de source au receveur
#                     sauf si la demande a deja été traité dans la boucle et donc done = True
        if stat.S_ISDIR(info[2]["mode"]): #permet de savoir plus bas si le fichier est un repertoire dans la source
            if "recursive" in OPT or "dirs" in OPT:
                is_file = False
            else:           #si l'option --dir et -r ne sont pas acitvent, on pass
                if ("vv" in OPT) & (not "quiet" in OPT): #print seulement si on a 2 verbose et pas de quiet en arg
                    message.print_log(f"{file} isn't a file, passing !")
                done = True
                pass
        

        for info_DEST in files_DEST:        #on cherche d'abord si le fichier est deja présent dans DEST
            if file > info_DEST[1]:         #file n'est pas dans DEST (car la liste est triée)
                break
            if file == info_DEST[1]:        #file est dans DEST
                if is_file:                 #file est un fichier
                    if stat.S_ISDIR(info_DEST[2]["mode"]):      #file est un dossier dans DEST
                        if "--force" in OPT:                #si --force est active, on remplace
                            message.send(wfd,10,info_DEST[1],OPT) #on suprime le dossier et on envoie le fichier                                    
                            break
                        else:
                            if ("vv" in OPT) & (not "quiet" in OPT): #on print seulement si on a 2 verboses en options
                                message.print_log(f"{file} is a directory in the destination, to replace it use --force, passing!")
                            done = True
                            break
                    else:                                   #file est bien un fichier dans DEST
                        if "ignore_existing" in OPT: #si  cette option est active, on pass
                            done = True
                            break 
                        if "ignore_times" in OPT: #si cette option est active, on update peut importe les autres options
                            message.send(wfd,11,(info[0],file),OPT)
                            signal.pause()
                            done = True
                            break

                        if "size_only" in OPT:      #on skip l'update si les tailles match dans la liste SRC et la liste DEST
                            if info[2]["size"] == info_DEST[2]["size"]:
                                done = True
                                break
                            else:
                                if "update" in OPT:  #la taille ne match pas, si --update est active, on skip toutes les updates des fichiers plus recents coté DEST(sauf si l'option I est active)
                                    if info_DEST[2]["time"] > info[2]["time"]:
                                        done = True
                                        break
                                message.send(wfd,11,(info[0],file),OPT) #on update le fichier dans DEST
                                signal.pause()                          #on attend le signal envoyé par le pere (le receveur) a la fin de la mise a jour 
                                done = True
                                break
                        
                        else:                               #pas d'option
                            if "update" in OPT:             #même chose qu'au dessus
                                    if info_DEST[2]["time"] > info[2]["time"]:
                                        done = True
                                        break
                            if (info[2]["size"] == info_DEST[2]["size"]) & (info[2]["time"] == info_DEST[2]["time"]): #on compare si la taille et la dare de derniere modif
                                done = True                                                                           #correspondent, on ne met pas a jour
                                break
                            else:    #sinon, mise a jour du fichier 
                                message.send(wfd,11,(info[0],file),OPT)
                                signal.pause()                        
                                done = True
                                break
                
                else: #le fichier coté SRC est un repertoire
                    if not stat.S_ISDIR(info_DEST[2]["mode"]): #si le fichier coté dest est un fichier (pas un repertoire), on le supr et on crée le fichier 
                        message.send(wfd,10,"",OPT)
                        message.send(wfd,7,file,OPT)
                        done = True
                        break
        if done:        #si la requete a deja été traité dans la boucle on ne faire rien
            pass
        else:           #sinon 
            if "existing" in OPT: #on ne crée pas de fichier côté DEST, ie on pass
                pass
            elif is_file: #si c'est un fichier (dans la SRC) on demande a l'envoyeur de transmettre le fichier au receveur 
                message.send(wfd,2,(info[0],file),OPT)
            else:   #sinon on crée le dossier 
                message.send(wfd,7,file,OPT)
    
    message.send(wfd,3,"fin",OPT)   #on previent l'envoyeur que c'est la fin de la transmission
    if ("v" in OPT) & (not "quiet" in OPT):  #print si verbose est acif
        message.print_log("Fin de la demande de fichiers!")
    sys.exit(0)


def quicksort(L): #fonction pour trier les listes en fonction du deuxieme élément
    n = len(L)
    if n < 2:
        return L
    low, same, high = [], [], []
    pivot = L[randint(0, n - 1)][1]
    for i in range(n):
        if L[i][1] < pivot:
            low.append(L[i])
        elif L[i][1] == pivot:
            same.append(L[i])
        elif L[i][1] > pivot:
            high.append(L[i])
    return quicksort(low) + same + quicksort(high)