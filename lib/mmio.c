#include <stdint.h>

#if defined(__riscv)
#define fence_ir __asm__ __volatile__ ("fence i,r" : : : "memory");
#define fence_wo __asm__ __volatile__ ("fence w,o" : : : "memory");
#else
#define fence_ir
#define fence_wo
#endif

#define itype(W) uint ## W ## _t

#define io_read(W) \
itype(W) mmio_read ## W (void *mmio) { \
	itype(W) ret = __atomic_load_n((itype(W)*)mmio, __ATOMIC_RELAXED); \
	fence_ir; \
	return ret; \
}

io_read(8)
io_read(16)
io_read(32)
io_read(64)

#define io_write(W) \
void mmio_write ## W (void *mmio, itype(W) val) { \
	fence_wo; \
	__atomic_store_n((itype(W)*)mmio, val, __ATOMIC_RELAXED); \
}

io_write(8)
io_write(16)
io_write(32)
io_write(64)

#define io_op_rw(op, W) \
itype(W) mmio_ ## op ## W (void *mmio, itype(W) val) { \
	fence_wo; \
	itype(W) ret = __atomic_ ## op ((itype(W)*)mmio, val, __ATOMIC_RELAXED); \
	fence_ir; \
	return ret; \
}

io_op_rw(exchange_n, 32)
io_op_rw(exchange_n, 64)
io_op_rw(fetch_add, 32)
io_op_rw(fetch_add, 64)
io_op_rw(fetch_sub, 32)
io_op_rw(fetch_sub, 64)
io_op_rw(fetch_and, 32)
io_op_rw(fetch_and, 64)
io_op_rw(fetch_xor, 32)
io_op_rw(fetch_xor, 64)
io_op_rw(fetch_or, 32)
io_op_rw(fetch_or, 64)
