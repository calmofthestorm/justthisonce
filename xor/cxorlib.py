from ctypes import *

STRING = c_char_p


__codecvt_noconv = 3
__codecvt_error = 2
__codecvt_partial = 1
__codecvt_ok = 0
class XorWorkUnit(Structure):
    pass
class _IO_FILE(Structure):
    pass
FILE = _IO_FILE
XorWorkUnit._fields_ = [
    ('output', POINTER(FILE)),
    ('inputs', POINTER(FILE) * 2),
    ('buf', c_char * 4194304 * 2),
]
class _G_fpos_t(Structure):
    pass
__off_t = c_long
class __mbstate_t(Structure):
    pass
class N11__mbstate_t4DOT_19E(Union):
    pass
N11__mbstate_t4DOT_19E._fields_ = [
    ('__wch', c_uint),
    ('__wchb', c_char * 4),
]
__mbstate_t._fields_ = [
    ('__count', c_int),
    ('__value', N11__mbstate_t4DOT_19E),
]
_G_fpos_t._fields_ = [
    ('__pos', __off_t),
    ('__state', __mbstate_t),
]
class _G_fpos64_t(Structure):
    pass
__off64_t = c_long
_G_fpos64_t._fields_ = [
    ('__pos', __off64_t),
    ('__state', __mbstate_t),
]
class _IO_jump_t(Structure):
    pass
_IO_jump_t._fields_ = [
]
_IO_lock_t = None
class _IO_marker(Structure):
    pass
_IO_marker._fields_ = [
    ('_next', POINTER(_IO_marker)),
    ('_sbuf', POINTER(_IO_FILE)),
    ('_pos', c_int),
]

# values for enumeration '__codecvt_result'
__codecvt_result = c_int # enum
size_t = c_ulong
_IO_FILE._fields_ = [
    ('_flags', c_int),
    ('_IO_read_ptr', STRING),
    ('_IO_read_end', STRING),
    ('_IO_read_base', STRING),
    ('_IO_write_base', STRING),
    ('_IO_write_ptr', STRING),
    ('_IO_write_end', STRING),
    ('_IO_buf_base', STRING),
    ('_IO_buf_end', STRING),
    ('_IO_save_base', STRING),
    ('_IO_backup_base', STRING),
    ('_IO_save_end', STRING),
    ('_markers', POINTER(_IO_marker)),
    ('_chain', POINTER(_IO_FILE)),
    ('_fileno', c_int),
    ('_flags2', c_int),
    ('_old_offset', __off_t),
    ('_cur_column', c_ushort),
    ('_vtable_offset', c_byte),
    ('_shortbuf', c_char * 1),
    ('_lock', POINTER(_IO_lock_t)),
    ('_offset', __off64_t),
    ('__pad1', c_void_p),
    ('__pad2', c_void_p),
    ('__pad3', c_void_p),
    ('__pad4', c_void_p),
    ('__pad5', size_t),
    ('_mode', c_int),
    ('_unused2', c_char * 20),
]
class _IO_FILE_plus(Structure):
    pass
_IO_FILE_plus._fields_ = [
]
__ssize_t = c_long
__io_read_fn = CFUNCTYPE(__ssize_t, c_void_p, STRING, size_t)
__io_write_fn = CFUNCTYPE(__ssize_t, c_void_p, STRING, size_t)
__io_seek_fn = CFUNCTYPE(c_int, c_void_p, POINTER(__off64_t), c_int)
__io_close_fn = CFUNCTYPE(c_int, c_void_p)
cookie_read_function_t = __io_read_fn
cookie_write_function_t = __io_write_fn
cookie_seek_function_t = __io_seek_fn
cookie_close_function_t = __io_close_fn
class _IO_cookie_io_functions_t(Structure):
    pass
_IO_cookie_io_functions_t._fields_ = [
    ('read', POINTER(__io_read_fn)),
    ('write', POINTER(__io_write_fn)),
    ('seek', POINTER(__io_seek_fn)),
    ('close', POINTER(__io_close_fn)),
]
cookie_io_functions_t = _IO_cookie_io_functions_t
class _IO_cookie_file(Structure):
    pass
_IO_cookie_file._fields_ = [
]
__FILE = _IO_FILE
class __va_list_tag(Structure):
    pass
__va_list_tag._fields_ = [
]
__gnuc_va_list = __va_list_tag * 1
va_list = __gnuc_va_list
fpos_t = _G_fpos_t
fpos64_t = _G_fpos64_t
class obstack(Structure):
    pass
obstack._fields_ = [
]
class div_t(Structure):
    pass
div_t._fields_ = [
    ('quot', c_int),
    ('rem', c_int),
]
class ldiv_t(Structure):
    pass
ldiv_t._fields_ = [
    ('quot', c_long),
    ('rem', c_long),
]
class lldiv_t(Structure):
    pass
lldiv_t._fields_ = [
    ('quot', c_longlong),
    ('rem', c_longlong),
]
class random_data(Structure):
    pass
int32_t = c_int32
random_data._fields_ = [
    ('fptr', POINTER(int32_t)),
    ('rptr', POINTER(int32_t)),
    ('state', POINTER(int32_t)),
    ('rand_type', c_int),
    ('rand_deg', c_int),
    ('rand_sep', c_int),
    ('end_ptr', POINTER(int32_t)),
]
class drand48_data(Structure):
    pass
drand48_data._fields_ = [
    ('__x', c_ushort * 3),
    ('__old_x', c_ushort * 3),
    ('__c', c_ushort),
    ('__init', c_ushort),
    ('__a', c_ulonglong),
]
__compar_fn_t = CFUNCTYPE(c_int, c_void_p, c_void_p)
comparison_fn_t = __compar_fn_t
__compar_d_fn_t = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p)
__clock_t = c_long
clock_t = __clock_t
__time_t = c_long
time_t = __time_t
__clockid_t = c_int
clockid_t = __clockid_t
__timer_t = c_void_p
timer_t = __timer_t
class timespec(Structure):
    pass
__syscall_slong_t = c_long
timespec._fields_ = [
    ('tv_sec', __time_t),
    ('tv_nsec', __syscall_slong_t),
]
pthread_t = c_ulong
class pthread_attr_t(Union):
    pass
pthread_attr_t._fields_ = [
    ('__size', c_char * 56),
    ('__align', c_long),
]
class __pthread_internal_list(Structure):
    pass
__pthread_internal_list._fields_ = [
    ('__prev', POINTER(__pthread_internal_list)),
    ('__next', POINTER(__pthread_internal_list)),
]
__pthread_list_t = __pthread_internal_list
class __pthread_mutex_s(Structure):
    pass
__pthread_mutex_s._fields_ = [
    ('__lock', c_int),
    ('__count', c_uint),
    ('__owner', c_int),
    ('__nusers', c_uint),
    ('__kind', c_int),
    ('__spins', c_int),
    ('__list', __pthread_list_t),
]
class pthread_mutex_t(Union):
    pass
pthread_mutex_t._fields_ = [
    ('__data', __pthread_mutex_s),
    ('__size', c_char * 40),
    ('__align', c_long),
]
class pthread_mutexattr_t(Union):
    pass
pthread_mutexattr_t._fields_ = [
    ('__size', c_char * 4),
    ('__align', c_int),
]
class N14pthread_cond_t4DOT_11E(Structure):
    pass
N14pthread_cond_t4DOT_11E._fields_ = [
    ('__lock', c_int),
    ('__futex', c_uint),
    ('__total_seq', c_ulonglong),
    ('__wakeup_seq', c_ulonglong),
    ('__woken_seq', c_ulonglong),
    ('__mutex', c_void_p),
    ('__nwaiters', c_uint),
    ('__broadcast_seq', c_uint),
]
class pthread_cond_t(Union):
    pass
pthread_cond_t._fields_ = [
    ('__data', N14pthread_cond_t4DOT_11E),
    ('__size', c_char * 48),
    ('__align', c_longlong),
]
class pthread_condattr_t(Union):
    pass
pthread_condattr_t._fields_ = [
    ('__size', c_char * 4),
    ('__align', c_int),
]
pthread_key_t = c_uint
pthread_once_t = c_int
class N16pthread_rwlock_t4DOT_14E(Structure):
    pass
N16pthread_rwlock_t4DOT_14E._fields_ = [
    ('__lock', c_int),
    ('__nr_readers', c_uint),
    ('__readers_wakeup', c_uint),
    ('__writer_wakeup', c_uint),
    ('__nr_readers_queued', c_uint),
    ('__nr_writers_queued', c_uint),
    ('__writer', c_int),
    ('__shared', c_int),
    ('__pad1', c_ulong),
    ('__pad2', c_ulong),
    ('__flags', c_uint),
]
class pthread_rwlock_t(Union):
    pass
pthread_rwlock_t._fields_ = [
    ('__data', N16pthread_rwlock_t4DOT_14E),
    ('__size', c_char * 56),
    ('__align', c_long),
]
class pthread_rwlockattr_t(Union):
    pass
pthread_rwlockattr_t._fields_ = [
    ('__size', c_char * 8),
    ('__align', c_long),
]
pthread_spinlock_t = c_int
class pthread_barrier_t(Union):
    pass
pthread_barrier_t._fields_ = [
    ('__size', c_char * 32),
    ('__align', c_long),
]
class pthread_barrierattr_t(Union):
    pass
pthread_barrierattr_t._fields_ = [
    ('__size', c_char * 4),
    ('__align', c_int),
]
__sig_atomic_t = c_int
class __sigset_t(Structure):
    pass
__sigset_t._fields_ = [
    ('__val', c_ulong * 16),
]
class timeval(Structure):
    pass
__suseconds_t = c_long
timeval._fields_ = [
    ('tv_sec', __time_t),
    ('tv_usec', __suseconds_t),
]
__u_char = c_ubyte
__u_short = c_ushort
__u_int = c_uint
__u_long = c_ulong
__int8_t = c_byte
__uint8_t = c_ubyte
__int16_t = c_short
__uint16_t = c_ushort
__int32_t = c_int
__uint32_t = c_uint
__int64_t = c_long
__uint64_t = c_ulong
__quad_t = c_long
__u_quad_t = c_ulong
__dev_t = c_ulong
__uid_t = c_uint
__gid_t = c_uint
__ino_t = c_ulong
__ino64_t = c_ulong
__mode_t = c_uint
__nlink_t = c_ulong
__pid_t = c_int
class __fsid_t(Structure):
    pass
__fsid_t._fields_ = [
    ('__val', c_int * 2),
]
__rlim_t = c_ulong
__rlim64_t = c_ulong
__id_t = c_uint
__useconds_t = c_uint
__daddr_t = c_int
__key_t = c_int
__blksize_t = c_long
__blkcnt_t = c_long
__blkcnt64_t = c_long
__fsblkcnt_t = c_ulong
__fsblkcnt64_t = c_ulong
__fsfilcnt_t = c_ulong
__fsfilcnt64_t = c_ulong
__fsword_t = c_long
__syscall_ulong_t = c_ulong
__loff_t = __off64_t
__qaddr_t = POINTER(__quad_t)
__caddr_t = STRING
__intptr_t = c_long
__socklen_t = c_uint
class wait(Union):
    pass
class N4wait3DOT_1E(Structure):
    pass
N4wait3DOT_1E._fields_ = [
    ('__w_termsig', c_uint, 7),
    ('__w_coredump', c_uint, 1),
    ('__w_retcode', c_uint, 8),
    ('', c_uint, 16),
]
class N4wait3DOT_2E(Structure):
    pass
N4wait3DOT_2E._fields_ = [
    ('__w_stopval', c_uint, 8),
    ('__w_stopsig', c_uint, 8),
    ('', c_uint, 16),
]
wait._fields_ = [
    ('w_status', c_int),
    ('__wait_terminated', N4wait3DOT_1E),
    ('__wait_stopped', N4wait3DOT_2E),
]
sigset_t = __sigset_t
__fd_mask = c_long
class fd_set(Structure):
    pass
fd_set._fields_ = [
    ('fds_bits', __fd_mask * 16),
]
fd_mask = __fd_mask
u_char = __u_char
u_short = __u_short
u_int = __u_int
u_long = __u_long
quad_t = __quad_t
u_quad_t = __u_quad_t
fsid_t = __fsid_t
loff_t = __loff_t
ino_t = __ino_t
ino64_t = __ino64_t
dev_t = __dev_t
gid_t = __gid_t
mode_t = __mode_t
nlink_t = __nlink_t
uid_t = __uid_t
off_t = __off_t
off64_t = __off64_t
pid_t = __pid_t
id_t = __id_t
ssize_t = __ssize_t
daddr_t = __daddr_t
caddr_t = __caddr_t
key_t = __key_t
useconds_t = __useconds_t
suseconds_t = __suseconds_t
ulong = c_ulong
ushort = c_ushort
uint = c_uint
int8_t = c_int8
int16_t = c_int16
int64_t = c_int64
u_int8_t = c_ubyte
u_int16_t = c_ushort
u_int32_t = c_uint
u_int64_t = c_ulong
register_t = c_long
blksize_t = __blksize_t
blkcnt_t = __blkcnt_t
fsblkcnt_t = __fsblkcnt_t
fsfilcnt_t = __fsfilcnt_t
blkcnt64_t = __blkcnt64_t
fsblkcnt64_t = __fsblkcnt64_t
fsfilcnt64_t = __fsfilcnt64_t
class __locale_struct(Structure):
    pass
class __locale_data(Structure):
    pass
__locale_struct._fields_ = [
    ('__locales', POINTER(__locale_data) * 13),
    ('__ctype_b', POINTER(c_ushort)),
    ('__ctype_tolower', POINTER(c_int)),
    ('__ctype_toupper', POINTER(c_int)),
    ('__names', STRING * 13),
]
__locale_data._fields_ = [
]
__locale_t = POINTER(__locale_struct)
locale_t = __locale_t
ptrdiff_t = c_long
__all__ = ['__uint16_t', '__pthread_mutex_s',
           'N16pthread_rwlock_t4DOT_14E', '__int16_t',
           'pthread_condattr_t', 'pthread_once_t', 'fsfilcnt_t',
           '__timer_t', 'FILE', 'pthread_mutexattr_t', 'size_t',
           'N14pthread_cond_t4DOT_11E', 'random_data', '__uint32_t',
           'fpos_t', 'fd_set', 'blkcnt_t', '__codecvt_partial',
           '__ino64_t', 'fsblkcnt64_t', '__qaddr_t', '__mode_t',
           '__loff_t', '__FILE', 'daddr_t', '__locale_data',
           'cookie_seek_function_t', 'N4wait3DOT_2E', 'fpos64_t',
           'uid_t', 'cookie_write_function_t', 'u_int64_t',
           'u_int16_t', '__time_t', 'sigset_t', '_G_fpos64_t',
           '_G_fpos_t', '_IO_jump_t', '__int32_t', 'pthread_rwlock_t',
           '__nlink_t', '__compar_fn_t', '__fsid_t',
           'cookie_close_function_t', '__uint64_t', 'mode_t',
           '__ssize_t', '__io_close_fn', '__va_list_tag', '__off64_t',
           '__fsword_t', '__fd_mask', 'int16_t', '__codecvt_ok',
           'clock_t', '__id_t', 'cookie_io_functions_t', '__sigset_t',
           '__clockid_t', '__useconds_t', 'div_t', 'id_t', 'ldiv_t',
           'va_list', 'pthread_barrier_t', 'u_int32_t', 'fd_mask',
           '__pthread_internal_list', '_IO_cookie_io_functions_t',
           '__codecvt_result', '__gnuc_va_list', '__intptr_t',
           '__u_long', 'wait', 'XorWorkUnit', '_IO_FILE_plus',
           'ushort', '__blkcnt_t', '__pthread_list_t', 'clockid_t',
           'pthread_attr_t', 'ptrdiff_t', 'caddr_t', 'uint',
           '__rlim64_t', 'ino_t', 'u_int8_t', 'int32_t', 'off64_t',
           '__blksize_t', '__syscall_ulong_t', 'pthread_spinlock_t',
           '__off_t', 'fsblkcnt_t', '__gid_t', 'u_quad_t', 'timespec',
           'register_t', '__syscall_slong_t', '__compar_d_fn_t',
           'obstack', 'fsfilcnt64_t', '__locale_struct',
           'comparison_fn_t', '__daddr_t', 'ino64_t',
           '_IO_cookie_file', '__sig_atomic_t', '__mbstate_t',
           '__uint8_t', '__io_seek_fn', '__u_char', '__fsblkcnt64_t',
           'u_int', '__caddr_t', '__blkcnt64_t', '__dev_t', 'gid_t',
           'pthread_barrierattr_t', '__suseconds_t', 'pid_t',
           'timer_t', 'quad_t', 'u_long', '__fsfilcnt64_t',
           '_IO_FILE', 'cookie_read_function_t', 'pthread_key_t',
           'blkcnt64_t', '__io_read_fn', 'loff_t', 'pthread_cond_t',
           'off_t', 'int64_t', '__fsblkcnt_t', '__rlim_t',
           'N4wait3DOT_1E', 'time_t', 'pthread_t', '__locale_t',
           'drand48_data', 'blksize_t', 'lldiv_t', '__quad_t',
           'timeval', '__codecvt_error', '_IO_marker', '__u_quad_t',
           '__u_short', '__int8_t', 'fsid_t', '__pid_t', 'ssize_t',
           'ulong', 'u_short', 'N11__mbstate_t4DOT_19E',
           '__io_write_fn', 'key_t', '__ino_t', 'int8_t',
           'useconds_t', '_IO_lock_t', 'nlink_t',
           'pthread_rwlockattr_t', 'locale_t', '__socklen_t',
           'u_char', '__u_int', 'pthread_mutex_t', '__int64_t',
           '__key_t', '__codecvt_noconv', '__clock_t', 'dev_t',
           '__uid_t', '__fsfilcnt_t', 'suseconds_t']
