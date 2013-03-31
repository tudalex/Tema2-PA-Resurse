#!/usr/bin/env python
import ctypes       # Allows us to make C calls
import ctypes.util  # Helps to find the C library

libc = ctypes.CDLL(ctypes.util.find_library("c"))
libproc = ctypes.CDLL(ctypes.util.find_library("proc"))

_calloc = libc.calloc
_free = libc.free

_proc_pidinfo = libproc.proc_pidinfo

PROC_pidTASKINFO = 4

class proc_taskinfo(ctypes.Structure):
  _fields_ = [("pti_virtual_size", ctypes.c_uint64),
              ("pti_resident_size", ctypes.c_uint64),
              ("pti_total_user", ctypes.c_uint64),
              ("pti_total_system", ctypes.c_uint64),
              ("pti_threads_user", ctypes.c_uint64),
              ("pti_threads_system", ctypes.c_uint64),
              ("pti_policy", ctypes.c_int32),
              ("pti_faults", ctypes.c_int32),
              ("pti_pageins", ctypes.c_int32),
              ("pti_cow_faults", ctypes.c_int32),
              ("pti_messages_sent", ctypes.c_int32),
              ("pti_messages_received", ctypes.c_int32),
              ("pti_syscalls_mach", ctypes.c_int32),
              ("pti_syscalls_unix", ctypes.c_int32),
              ("pti_csw", ctypes.c_int32),
              ("pti_threadnum", ctypes.c_int32),
              ("pti_numrunning", ctypes.c_int32),
              ("pti_priority", ctypes.c_int32)]

class timeval(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long),
                ("tv_usec", ctypes.c_long)]
              
PROC_TASKINFO_SIZE = ctypes.sizeof(proc_taskinfo)

def get_ctypes_errno():
  errno_pointer = ctypes.cast(libc.errno, ctypes.POINTER(ctypes.c_int32))
  err_val = errno_pointer.contents
  return err_val.value

def get_ctypes_error_str():
  errornum = get_ctypes_errno()
  return ctypes.cast(libc.strerror(errornum), ctypes.c_char_p).value
 

def get_process_cpu_time(pid):
  _calloc.restype = ctypes.POINTER(proc_taskinfo)
  last_proc_info_struct = _calloc(1, PROC_TASKINFO_SIZE)
  status = _proc_pidinfo(pid, PROC_pidTASKINFO, ctypes.c_uint64(0),  last_proc_info_struct, PROC_TASKINFO_SIZE)
  if status is 0:
    raise Exception,"Errno:"+str(get_ctypes_errno())+", Error: "+get_ctypes_error_str()
  proc_info = last_proc_info_struct.contents
  
  # Get the total time from the user time and system time
  # Divide 1 billion since time is in nanoseconds
  print "Calculating CPU Time"
  total_time = proc_info.pti_total_user/1000000000.0 + proc_info.pti_total_system/1000000000.0

  if last_proc_info_struct != None:
    _free(last_proc_info_struct)
  return total_time