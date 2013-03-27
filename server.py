#!/usr/bin/env python
import subprocess
import sys
from subprocess import PIPE
import argparse
from threading import Timer
import time
import resource
import os


class Error(Exception):
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)

bufsize = 512
movement = [
  ( 0, 1), #N  0
  ( 1, 1), #NE 1
  ( 1, 0), #E  2
  ( 1,-1), #SE 3
  ( 0,-1), #S  4
  (-1,-1), #SV 5
  (-1, 0), #V  6
  (-1, 1)  #NV 7
]
touched_vertices = set([(0, 0)])
lines = set()

for i in xrange(-5, 5): #limitari pentru laterala
  touched_vertices.add((4,i))
  touched_vertices.add((-4,i))
  touched_vertices.add((4,i+1))
  touched_vertices.add((-4,i+1))
  lines.add(( (4, i), (4, i+1)))
  lines.add(( (-4, i), (-4, i+1)))
for i in xrange(-4, 4): #limitari sus si jos
  if i<-1 or i >0:
    touched_vertices.add((i, 5))
    touched_vertices.add((i, -5))
    touched_vertices.add((i+1, 5))
    touched_vertices.add((i+1, -5))
    lines.add(( (i, 5), (i+1, 5)))
    lines.add(( (i, -5), (i+1, -5)))

for i in [-6, 6]:
  touched_vertices.add((1, i))
  touched_vertices.add((-1, i))
for i in [-1,1]:
  lines.add(( (i,6), (i,5)))
  lines.add(( (i,-5),(i,-6)))

lines.add(( (-2, 5), (-1, 6)))
lines.add(( (2, 5), (1, 6)))
lines.add(( (2, -5), (1, -6)))
lines.add(( (-2, -5), (-1, -6)))

def move(direction, position):
  return (position[0]+movement[direction][0],pos[1]+movement[direction][1])

pos = (0, 0)

parser = argparse.ArgumentParser()
parser.add_argument("fisier1", help="Executabilul ce determina primul jucator.")
parser.add_argument("fisier2", help="Executabilul ce determina al doilea jucator.")
parser.add_argument("-t", "--timeout", dest="timeout", default=10.0, type=float,
                  help="Timpul pe care sa il astepte dupa input de la unul din programe.")
parser.add_argument("-v", "--verbose", dest="verbose", default=True, #TODO(tudalex): Change for production
                  help="Programul va genera output verbose. Bun pentru debugging.")
args = parser.parse_args()

# Deschidem fisierul de log pentru viewer

viewer_log = open('viewer_log', 'w')
finished = False

def can_move(old_pos, new_pos):
  if (new_pos,pos) in lines or  (pos, new_pos) in lines:
    raise Error("Illegal move, move already made.")
  if abs(new_pos[0]) > 4:
    raise Error("Illegal move, out of field.")
  if abs(new_pos[1]) > 5 and abs(new_pos[0]) > 1:
    raise Error("Illegal move, out of field.")
  
def legal_move( moves ):
  viewer_log.write('{0} {1} '.format(current, len(moves)))
  moves = [int(x) for x in moves]
  global pos, finished
  remaining_moves = 1
  for x in moves:
    remaining_moves = remaining_moves - 1
    if remaining_moves<0:
      raise Error("Illegal move, too many moves.")
    new_pos = move(x, pos)
    can_move(pos, new_pos)

    if new_pos in touched_vertices:
      remaining_moves = remaining_moves + 1
    else:
      touched_vertices.add(new_pos)
    
    lines.add((pos, new_pos))
    pos = new_pos
    viewer_log.write('{0} '.format(x))
    viewer_log.flush()

  if remaining_moves > 0 and abs(pos[1])<6:
    print >>sys.stderr, "Checking for remaining_moves"
    count = 0
    for i in xrange(len(movement)):
      new_pos = move(i, pos)
      try:
        can_move(pos, new_pos)
        count +=1
        
        print >>sys.stderr, "Player could move to", new_pos, "from", pos
      except Error as e: 
        pass
    if count == 0:
      print >>sys.stderr, "Player ", current, "can't move anymore."
      finished = True
    else:
      raise Error("Illegal moves, player still had to move.")
  viewer_log.write('\n')

#Creeam cele 2 procese
p = []
p.append(subprocess.Popen(args.fisier1.split(' '),bufsize=bufsize, stdin=PIPE, stdout=PIPE, close_fds=False))
p.append(subprocess.Popen(args.fisier2.split(' '),bufsize=bufsize, stdin=PIPE, stdout=PIPE, close_fds=False))
#Pornim primul proces
current = 0; #TODO(tudalex): Randomizam asta?
previous = 1 - current;
p[current].stdin.write('S\n')
p[current].stdin.flush()


def no_answer():
  print >>sys.stderr, "Procesul "+ str(current)+" a dat timeout"
  for x in p:
    if x.poll() is None:
      try:
        x.kill()
      except Exception as e:
        pass
def get_run_time(pid):
  if sys.platform == 'darwin':
    import macos_time
    return macos_time.get_process_cpu_time(pid)
  if sys.platform == 'linux2':
    f = open("/proc/"+str(pid)+"/stat","r")
    t = f.readline()
    f.close()
    return float(t.split(' ')[13])/float(os.sysconf(2))
  if sys.platform == 'win32':
    return 0
    import win32process  #TODO:Test that this actually works on windows which 
    d = win32process.GetProcessTimes(pid)
    return (d['UserTime'] / WIN32_PROCESS_TIMES_TICKS_PER_SECOND,
        d['KernelTime'] / WIN32_PROCESS_TIMES_TICKS_PER_SECOND)

old_run_time = [0.0, 0.0]

try:
  while not finished:
    t = Timer(2*args.timeout, no_answer)
    t.start()
    buf = p[current].stdout.readline() #citim de pe procesul curent
    t.cancel()
    time = get_run_time(p[current].pid)
    print >>sys.stderr, "It took",(time - old_run_time[current] ), "to run this turn."
    if (time - old_run_time[current] > args.timeout):
      raise Error("Timeout.")
    old_run_time[current] = time    

    print >>sys.stderr, str(current)+": "+buf
    #intercept and mangle data here
    if len(buf) == 0:
      if p[current].poll() is not None:
        raise Error("Procesul "+str(current)+" a murit.")
      continue
    message =  [ x.strip() for x in buf.split(' ')]
    if (message[0] == 'M'): # Putem astepta alte mesaje inafara de M?
      print >>sys.stderr, message
      
      print >>sys.stderr, message
      if (int(message[1]) != len(message[2:]) or (int(message[1]) == 0)):
        raise Error("Message of incorrect length from "+str(current));
      test = [x for x in message[2:] if int(x) > 7 or int(x) < 0]
      if len(test)> 0: # Testam daca mutarile sunt proaste
        raise Error("Incorrect directions: "+" ".join(test)) 
      message = message[0:2] + [str((int(x)+4)%8) for x in message[2:]] #Inversam mutarile
      if current == 0:
        legal_move([str((int(x)+4)%8) for x in message[2:]])
      else:
        legal_move(message[2:])
    else:
      raise Error("Not expected message.")

    if abs(pos[1]) >= 6 or finished: #Jocul s-a terminat
      if not finished:
          current = 1-current
      for x in p:
        x.stdin.write('F\n')
        x.stdin.flush()
      finished = True
    else:
      buf =  " ".join(message)
      print >>sys.stderr, "SERVER: Trimit mesajul \""+buf+"\" catre clientul"+str(previous)
      if p[previous].poll() is None: # O incercare proasta de a ma prinde daca un proces a murit
        try:
          p[previous].stdin.write(buf+"\n")
          p[previous].stdin.flush()
        except IOError as e:
          print "I/O error({0}): {1}".format(e.errno, e.strerror)
          print previous
          
      else:
        raise Error("Procesul "+str(previous)+" a murit.")

    
    current = 1 - current
    previous = 1 - current

except (KeyboardInterrupt, Error) as e:
  print e
  viewer_log.close()
  for x in p:
    try:
      x.kill()
    except OSError, IOError:
      pass


else:
  print "Jucatorul "+str(current)+" a castigat jocul."
