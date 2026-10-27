import channel #-
import random, math #-
from constChord import * #-
#-
class ChordNode:
#-
  def __init__(self, channelID, nodeID, nodeSet, nBits): #- 
    self.channel = channel.Channel(channelID)            # Cria referência ao canal real #-
    self.channel.join(nodeID)                            #-
#-
    self.nBits   = nBits                                 # Número de bits do espaço de IDs #-
    self.nodeSet = nodeSet                               # Nós Chord participantes #-
    self.MAXPROC = pow(2,nBits)                          # Número máximo de processos #-
    self.nodeID  = int(nodeID)                           # Este nó #-
    self.nodeInd = self.nodeSet.index(nodeID)            # Posição deste nó no anel Chord #-
    self.FT      = [None for i in range(self.nBits+2)]   # FT[0] é o predecessor, FT[nBits+2] é este nó #-
#-
  def __inbetween(self, key, lwb, upb):                                         #-
    if lwb <= upb:                                                            #-
      result = (lwb <= key and key < upb)                                         #-
    else:                                                                     #- 
      result = ((lwb <= key and key < upb + self.MAXPROC) or (lwb <= key + self.MAXPROC and key < upb)) #-
    return result #-

  def __succNode(self, key):
    if (key <= self.nodeSet[0] or
        key > self.nodeSet[len(self.nodeSet)-1]): # a chave está no segmento pelo qual
      return self.nodeSet[0]                      # este nó é responsável
    for i in range(1,len(self.nodeSet)):
      if (key <= self.nodeSet[i]):                # a chave está no segmento pelo qual
        return self.nodeSet[i]                    # o nó (i+1) pode ser responsável
    
  def __finger(self, i):
    return self.__succNode((self.nodeID + pow(2,i-1)) % self.MAXPROC) # succ(p+2^(i-1))

  def __recomputeFingerTable(self): 
    self.FT[0]  = self.nodeSet[(self.nodeInd - 1)%len(self.nodeSet)] # Predecessor
    self.FT[1:] = [self.__finger(i) for i in range(1,self.nBits+1)]  # Sucessores
    self.FT.append(self.nodeID)                                      # Este nó

  def __localSuccNode(self, key):
    if self.__inbetween(key, self.FT[0]+1, self.nodeID+1):   # chave em (pred, este]
      return self.nodeID                                     # este nó é responsável
    elif self.__inbetween(key, self.nodeID+1, self.FT[1]):   # chave em (este, FT[1]]
      return self.FT[1]                                      # o sucessor é responsável
    for i in range(1, self.nBits+2):                         # percorre o restante da FT
      if self.__inbetween(key, self.FT[i], self.FT[(i+1)]):  # chave em [FT[i], FT[i+1])
        return self.FT[i]                                    # FT[i] é responsável
#- 
  def run(self): #-
    self.__recomputeFingerTable() #-
    print(">>>",self.nodeID,": ",self.FT) #-
#-
    while True: #-
      message = self.channel.recvFromAny()                   # Espera qualquer requisição #-
      sender  = message[0]                                   # Identifica o remetente #-
      request = message[1]                                   # E a requisição em si #-
      if request[0] == STOP: #-
        break #-
      if request[0] == LOOKUP_REQ:                           # Uma requisição de busca #-
        nextID = self.__localSuccNode(request[1])            # busca o próximo nó #-
        self.channel.sendTo(sender, (LOOKUP_REP, nextID)) # devolve ao remetente #-
    return #-
#-
class ChordClient: #-
  def __init__(self, channelID, nodeID, nodeSet, nBits):                 #-
    self.channel = channel.Channel(channelID) #-
    self.channel.join(nodeID) #-
#-
    self.nodeID  = nodeID #-
    self.nodeSet = nodeSet #-
    self.nBits   = nBits #-
#-
  def run(self, numberOfRuns): #-
    procs = self.nodeSet #-
    procs.sort() #-
#-
    for k in range(numberOfRuns): #-
      p   = 28 # procs[random.randint(0,len(procs)-1)] #-
      key = 12 # random.randint(0,pow(2,self.nBits)) #-
      route = [p] #-
#-
      self.channel.sendTo(p, (LOOKUP_REQ, key) ) #-
      msg = self.channel.recvFromAny() #-
#-      
      route.append(msg[1][1]) #-
#-
      while msg[1][1] != p: #-
        p = msg[1][1] #-
        self.channel.sendTo(p,(LOOKUP_REQ, key)) #-
        msg = self.channel.recvFrom(p) #-
        route.append(msg[1][1]) #-
      print(self.nodeID, "Client got answer for", key, "from", p, "through route", route) #-
#-
    self.channel.sendTo(procs, (STOP)) #-
