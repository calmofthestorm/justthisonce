default: all

cxor.so: cxor.c cxor.h
	gcc cxor.c -fPIC -shared -Wall -pedantic -O3 -o cxor.so

bindings: cxor.h cxor.c
	h2xml.py `pwd`/cxor.h -o cxor.xml
	xml2py.py `pwd`/cxor.xml -o cxorlib.py

test: cxor.h cxor.c test_cxor.c
	gcc test_cxor.c -O3 ./cxor.so -o test
	./test

all: bindings cxor.so
