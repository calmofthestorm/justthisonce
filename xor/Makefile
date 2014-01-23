default: all

cxor.so: cxor.c cxor.h
	$(CC) -fPIC -shared -Wall -Werror -O3 -o $@ -std=c99 -g $< -march=native

bindings: cxor.so cxor.h
	h2xml.py `pwd`/cxor.h -o cxor.xml
	xml2py.py `pwd`/cxor.xml -o cxorlib.py

test: cxor.so test_cxor.c
	$(CC) test_cxor.c -O3 ./cxor.so -o $@ --std=c99 -g
	./test

coverage: test
	$(CC) cxor.c test_cxor.c -o test -fprofile-arcs -ftest-coverage -pg --std=c99
	./test
	gcov cxor.c

all: bindings cxor.so

clean:
	-rm -f cxor.so test

.PHONY: all clean
