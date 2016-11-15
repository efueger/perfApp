CXX      = mpic++
CXXFLAGS = -O2 -DUSE_MPI -march=native -funroll-loops -ffast-math -ftree-vectorize -g # Add -g to get function names in perf profile

all:
	$(CXX) $(CXXFLAGS) -o pfaFlopsCacheMisses.exe ../pfaFlopsCacheMisses.cpp

.PHONY: clean
clean:
	rm -f *.o *.a *.exe
