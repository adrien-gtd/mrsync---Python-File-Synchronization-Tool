import os,sys,pickle,signal,time

def alarm_(sig,fram): #si l'option "timeout" est active
    print_log("Error, I/O timeout")
    sys.exit(30)

def send(fd,tag,v,OPT):             #permet d'envoyer un message qui peut être lu par receive
    signal.signal(signal.SIGALRM,alarm_)
    message = pickle.dumps(v)
    length = len(message).to_bytes(2,byteorder="big") 
    ids = tag.to_bytes(3,byteorder="big")
    data = ids + length + message       #on envoie d'abord le tag, la taille puis le message

    if "timeout" in OPT:  #option timeout
        time_ = OPT.index("timeout") + 1
        signal.alarm(time_)

    os.write(fd,data)

    if "timeout" in OPT:    #option timeout
        signal.alarm(0)


def receive(fd,OPT):        #parmet de lire le message envoyer avec la fonction send
    tag = int.from_bytes(os.read(fd,3),byteorder="big")                 #on lit d'abord le tag
    length = int.from_bytes(os.read(fd,2),byteorder="big")              #puis la taille du message 

    if "timeout" in OPT:      #--timeout
        time_ = OPT.index("timeout") + 1
        signal.alarm(time_)

    message = os.read(fd,length)                                        #et enfin le message
    if len(message) < length:
        time.sleep(0.1)                                                 #si le buffer de la pipe est full, on endort le processus 0.1s pour redonné la main a 
        message = message + os.read(fd,length - len(message))           #l'autre processus pour qu'il envoie la fin du message, un peu bricolé mais ça marche

    if "timeout" in OPT:    #option timeout
        signal.alarm(0) 

    v = pickle.loads(message) #byte -> struct 
    return (tag,v)                             #return la structur et le tag

def print_log(message):                 #permet d'ecrire des log sur la sortie d'erreur, utile pour le demon et le mode ssh notamment
    print(message,1,file=sys.stderr)
