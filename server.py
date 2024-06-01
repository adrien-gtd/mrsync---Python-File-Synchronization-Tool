import os,filelist,sys,receiver,socket,message,sender,signal


def server(DEST,OPT): #fichier peut utile, j'ai géré touts les aspects serveurs dans mrsync.py
    receiver.receiver(DEST,OPT,1,0)


