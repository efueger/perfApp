CXX      = g++
CXXFLAGS = -O2 -march=native -funroll-loops -ffast-math -ftree-vectorize -g -fopenmp # Add -g to get function names in perf profile

all:
	$(CXX) $(CXXFLAGS) -o pfaFlopsCacheMisses.exe ../pfaFlopsCacheMisses.cpp

.PHONY: clean
clean:
	rm -f *.o *.a *.exe
