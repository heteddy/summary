# 总makefile



```makefile
XX = g++
AR = ar
ARFLAG = -rcs
CFLAGS = -g 
 
CLIBS = -L./lib/ -lSender -lReceiver -lResponser  -lpthread
 
SUBDIRS = ./receiver ./responser ./sender
 
INCLUDES = $(wildcard ./include/*.h ./sender/*.h ./receiver/*.h ./responser/*.h) # INCLUDE = a.h b.h ... can't be defined like "INCLUDE = ./*.h"
#SOURCES = $(wildcard ./*.cpp ./sender/*.cpp ./receiver/*.cpp ./responser/*.cpp)
INCLUDE_DIRS = -I./include -I./sender/ -I./receiver/ -I./responser/ #指定头文件目录，代码中就不需要把头文件的完整路径写出来了
 
TARGET = mainApp
#OBJECTS = $(patsubst %.cpp,%.o,$(SOURCES))
OBJECTS = main.o
 
export XX CFLAGS AR ARFLAG
 
$(TARGET) : $(OBJECTS) $(SUBDIRS)
	$(XX) $< -o $@ $(CLIBS)     # $< 表示依赖列表的第一个 也就是 $(OBJECTS)
	
$(OBJECTS) : %.o : %.cpp 
	$(XX) -c $(CFLAGS) $< -o $@ $(INCLUDE_DIRS)
	
$(SUBDIRS):ECHO
	+$(MAKE) -C $@
ECHO:
	@echo $(SUBDIRS)
	@echo begin compile
.PHONY : clean
clean:
	for dir in $(SUBDIRS);\
	do $(MAKE) -C $$dir clean||exit 1;\
	done
	rm -rf $(TARGET) $(OBJECTS)  ./lib/*.a

```

# 子makefile



```makefile
LIB_DIR = ./../lib/
TOP_DIR = ./..

SOURCES = $(wildcard ./*.cpp)
INCLUDE_DIRS = -I$(TOP_DIR)/include  -I$(TOP_DIR)/responser/ -I./ 

TARGET = libReceiver.a
OBJECTS = $(patsubst %.cpp,%.o,$(SOURCES))

$(TARGET) : $(OBJECTS)
	$(AR) $(ARFLAG) $@ $^
	cp $@ $(LIB_DIR)
	
$(OBJECTS) : %.o : %.cpp 
	$(XX) -c $(CFLAGS) $< -o $@ $(INCLUDE_DIRS)

.PHONY : clean
clean:
	rm -rf $(TARGET) $(OBJECTS)

```

赋值符号：=基本赋值，:=覆盖之前的指，?=如果没有值则赋值，+=继续添加后面的值。



# 多文件

```makefile
# 方便起见一般都会先定义编译器链接器
CC = gcc 
LD = gcc

# 正则表达式表示目录下所有.c文件，相当于：SRCS = main.c a.c b.c
SRCS = $(wildcard *.c)

# OBJS表示SRCS中把列表中的.c全部替换为.o，相当于：OBJS = main.o a.o b.o
OBJS = $(patsubst %c, %o, $(SRCS))

# 可执行文件的名字
TARGET = Hello

# .PHONE伪目标，具体含义百度一下一大堆介绍
.PHONY:all clean

# 要生成的目标文件
all: $(TARGET)

# 第一行依赖关系：冒号后面为依赖的文件，相当于Hello: main.o a.o b.o
# 第二行规则：$@表示目标文件，$^表示所有依赖文件，$<表示第一个依赖文件
$(TARGET): $(OBJS)
	$(LD) -o $@ $^

# 上一句目标文件依赖一大堆.o文件，这句表示所有.o都由相应名字的.c文件自动生成
%.o:%.c
	$(CC) -c $^

# make clean删除所有.o和目标文件
clean:
	rm -f $(OBJS) $(TARGET)

```

# 多目录

```makefile
C_SRC = $(wildcard *.c)
C_OBJ = $(patsubst %c, %o, $(C_SRC))
# 目标文件也是多个
TARGETLIST = $(patsubst %.c, %, $(C_SRC))

.PHONY:all clean
# 这句不写规则的语句可以自动把相应的a.c b.c编译成a b，神奇~
all:${TARGETLIST}

clean:  
	rm -f ${TARGETLIST} *.o 
```



# 指定目录

```makefile
CC = cc
LD = cc
SRCS = $(wildcard *.cpp)
OBJS = $(patsubst %cpp, %o, $(SRCS))
# -I指定头文件目录
INCLUDE = -I./include
# -L指定库文件目录，-l指定静态库名字(去掉文件名中的lib前缀和.a后缀)
LIB = -L./libs -ltomcrypt
# 开启编译warning和设置优化等级
CFLAGS = -Wall -O2

TARGET = LibtomDemo

.PHONY:all clean

all: $(TARGET)
# 链接时候指定库文件目录及库文件名
$(TARGET): $(OBJS)
	$(LD) -o $@ $^ $(LIB)
 
# 编译时候指定头文件目录
%.o:%.cpp
	$(CC) -c $^ $(INCLUDE) $(CFLAGS) 

clean:
	rm -f $(OBJS) $(TARGET)
```

# 遍历子目录

```makefile
.PHONY:all clean
# 排除目录
exclude_dirs := .git
# 显示深度为1的子目录
dirs := $(shell find . -type d -maxdepth 1)
# 去掉获取到目录名称前面的./
dirs := $(basename $(patsubst ./%, %, $(dirs)))
# 过滤指定目录
dirs := $(filter-out $(exclude_dirs), $(dirs))

all:
    $(foreach N,$(dirs),make -C $(N);)
clean:
    $(foreach N,$(dirs),make -C $(N) clean;)
```

