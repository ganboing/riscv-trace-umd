#include <stdint.h>
#include <time.h>

#if defined(__riscv)
#define fence_ir __asm__ __volatile__ ("fence i,r" : : : "memory");
#define fence_wo __asm__ __volatile__ ("fence w,o" : : : "memory");
#else
#define fence_ir
#define fence_wo
#endif

#define itype(W) uint ## W ## _t
#define ptype(W) volatile itype(W) *

#define io_read(W) \
itype(W) mmio_read ## W (void *mmio) { \
	itype(W) ret = __atomic_load_n((ptype(W))mmio, __ATOMIC_RELAXED); \
	fence_ir; \
	return ret; \
}

io_read(8)
io_read(16)
io_read(32)
io_read(64)

itype(64) mmio_read32x2 (void *mmio) {\
    itype(64) ret = __atomic_load_n((ptype(32))mmio + 1, __ATOMIC_RELAXED); \
    ret <<= 32;
    ret |= __atomic_load_n((ptype(32))mmio, __ATOMIC_RELAXED); \
	fence_ir; \
	return ret; \
}

#define io_read_diff(W, N) \
itype(W) mmio_read ## N ## _diff(void *mmio, uint64_t duration) { \
    struct timespec ts1 = {}, ts2 = {}; \
	clock_gettime(CLOCK_MONOTONIC_RAW, &ts1); \
	itype(W) ret = mmio_read ## N (mmio); \
	for (;;) { \
	    clock_gettime(CLOCK_MONOTONIC_RAW, &ts2); \
	    uint64_t diff = 1000ULL * 1000 * 1000 * (ts2.tv_sec - ts1.tv_sec); \
	    diff += ts2.tv_nsec; \
	    diff -= ts1.tv_nsec; \
	    if (diff >= duration) \
	        break; \
	} \
	ret = mmio_read ## N (mmio) - ret; \
	return ret; \
}

io_read_diff(8, 8)
io_read_diff(16, 16)
io_read_diff(32, 32)
io_read_diff(64, 64)
io_read_diff(64, 32x2)

#define io_write(W) \
void mmio_write ## W (void *mmio, itype(W) val) { \
	fence_wo; \
	__atomic_store_n((ptype(W))mmio, val, __ATOMIC_RELAXED); \
}

io_write(8)
io_write(16)
io_write(32)
io_write(64)

void mmio_write32x2 (void *mmio, itype(64) val) {\
	fence_wo; \
	__atomic_store_n((ptype(32))mmio + 1, val >> 32, __ATOMIC_RELAXED); \
	__atomic_store_n((ptype(32))mmio, val, __ATOMIC_RELAXED); \
}

#define io_op_rw(op, W) \
itype(W) mmio_ ## op ## W (void *mmio, itype(W) val) { \
	fence_wo; \
	itype(W) ret = __atomic_ ## op ((ptype(W))mmio, val, __ATOMIC_RELAXED); \
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
