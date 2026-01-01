exe = ldb

CC = g++
AR = ar
ARFLAG = -rcs
CFLAGS = -g
SOURCES = $(wildcard ./*.cpp)
INCLUDE_DIRS += -I../leveldb/leveldb/include \
                -I./

LIB_DIRS +=
CLIBS = -L ./leveldb/build/

ldb:
    ${CC} ${CFLAGS}
