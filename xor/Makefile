default: all

cxor.so:
	gcc cxor.c -fPIC -shared -Wall -pedantic -O3 -o cxor.so

bindings:
	h2xml.py `pwd`/cxor.h -o cxor.xml
	xml2py.py `pwd`/cxor.xml -o cxorlib.py

all: bindings cxor.so
