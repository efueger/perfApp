#include <iostream> // cout, cerr
#include <sstream>  // string stream
#include <cstdlib>  // getenv

#ifdef USE_MPI
#include <mpi.h>    // MPI
#endif

void doCompute(double & a, double & b, double & c, double & d, double & e) {
  a += 2.   * b + 0.4;
  c *= 0.25 * d - 0.2;
  a -= 3.   * b * 0.7;
  c /= 4.   * d * 0.8;
  e += a * b + d * c;
  b += 0.25 * e + 0.1;
  d += 0.33 * e - 0.2;
}

void doFlops(double & a, double & b, double & c, double & d, double & e) {
  #pragma omp parallel for
  for(unsigned int i = 0; i < 1000000; i++) doCompute(a, b, c, d, e);
}

void doSwap(unsigned long long int i, unsigned long long int j, unsigned long long int k, unsigned long long int ll,
            unsigned long long int n, double * p,
            unsigned int l1Size, double * pL1, unsigned int l2Size, double * pL2, unsigned int l3Size, double * pL3) {
  unsigned long long int nn = n/4;
  double * p1 = p; double * p2 = p+nn; double * p3 = p+2*nn; double * p4 = p+3*nn;
  double tmp = 0.;
  tmp = pL1[i]; pL1[i] = pL1[l1Size-1-i]; pL1[l1Size-1-i] = tmp;
  tmp = p1[ll]; p1[ll] =     p1[nn-1-ll];     p1[nn-1-ll] = tmp;
  tmp = p3[ll]; p3[ll] =     p3[nn-1-ll];     p3[nn-1-ll] = tmp;
  tmp = pL2[j]; pL2[j] = pL2[l2Size-1-j]; pL2[l2Size-1-j] = tmp;
  tmp = p2[ll]; p2[ll] =     p2[nn-1-ll];     p2[nn-1-ll] = tmp;
  tmp = p4[ll]; p4[ll] =     p4[nn-1-ll];     p4[nn-1-ll] = tmp;
  tmp = pL3[k]; pL3[k] = pL3[l3Size-1-k]; pL3[l3Size-1-k] = tmp;
}

void doCacheMisses(unsigned long long int n, double * p,
                   unsigned int l1Size, double * pL1, unsigned int l2Size, double * pL2, unsigned int l3Size, double * pL3) {
  unsigned long long int i = 0, j = 0, k = 0, nn = n/4;
  #pragma omp parallel for
  for(unsigned long long int l = 0; l < nn; l++) {
    unsigned long long int ll = l;
    i  += l1Size/2; if(i  >= l1Size) i  -= l1Size;
    j  += l2Size/2; if(j  >= l2Size) j  -= l2Size;
    k  += l3Size/2; if(k  >= l3Size) k  -= l3Size;
    ll +=     nn/2; if(ll >=     nn) ll -=     nn;
    doSwap(i, j, k, ll, n, p, l1Size, pL1, l2Size, pL2, l3Size, pL3);
  }
}

void doBarrier(void) { // A function in a binary can be watched over by perf-probe.
  #pragma omp barrier
  #ifdef USE_MPI
  MPI_Barrier(MPI_COMM_WORLD); // It seems impossible to probe directly MPI_Barrier with perf-probe.
  #endif
}

int main(int argc, char ** argv) {
  #ifdef USE_MPI
  MPI_Init(&argc, &argv);
  #endif

  // Get parameters

  unsigned int cmAlloc = 1;
  if(argc >= 2) {
    std::stringstream str(argv[1]); str >> cmAlloc;
    if(getenv("PFA_VERBOSE")) std::cout << "cmAlloc = " << cmAlloc << std::endl;
  }
  unsigned int cmFactor = 1;
  if(argc >= 3) {
    std::stringstream str(argv[2]); str >> cmFactor;
    if(getenv("PFA_VERBOSE")) std::cout << "cmFactor = " << cmFactor << std::endl;
  }
  unsigned int nbAveCM = 1;
  if(argc >= 4) {
    std::stringstream str(argv[3]); str >> nbAveCM;
    if(getenv("PFA_VERBOSE")) std::cout << "nbAveCM = " << nbAveCM << std::endl;
  }
  unsigned int nbAveGF = 1;
  if(argc >= 5) {
    std::stringstream str(argv[4]); str >> nbAveGF;
    if(getenv("PFA_VERBOSE")) std::cout << "nbAveGF = " << nbAveGF << std::endl;
  }

  // Cache misses

  unsigned long long int n = cmAlloc * 1024 * 1024 * 1024 / sizeof(double); // Allocate 1 GB
  double * p = new double [n];
  unsigned int l1Size = cmFactor *   32 * 1024. / sizeof(double);
  double * pL1 = new double [l1Size]; // Fill L1 to enhance cache misses
  unsigned int l2Size = cmFactor *  256 * 1024. / sizeof(double);
  double * pL2 = new double [l2Size]; // Fill L2 to enhance cache misses
  unsigned int l3Size = cmFactor * 4096 * 1024. / sizeof(double);
  double * pL3 = new double [l3Size]; // Fill L3 to enhance cache misses
  for(unsigned int i = 0; i < nbAveCM; i++) {
    for(unsigned int a = 0; a < l1Size; a++) pL1[a] = 1.;
    for(unsigned int b = 0; b < l2Size; b++) pL2[b] = 1.;
    for(unsigned int c = 0; c < l3Size; c++) pL3[c] = 1.;
    for(unsigned int d = 0; d < n;      d++) p[d]   = 1.;
    doCacheMisses(n, p, l1Size, pL1, l2Size, pL2, l3Size, pL3);
  }
  if(pL1) { delete [] pL1; pL1 = NULL; }
  if(pL2) { delete [] pL2; pL2 = NULL; }
  if(pL3) { delete [] pL3; pL3 = NULL; }
  if(p)   { delete [] p;   p   = NULL; }

  // Barrier

  doBarrier();

  // Flops

  double a = 0., b = 1., c = 0., d = 1., e = 0.;
  for(unsigned int i = 0; i < nbAveGF; i++) {
    a = 0., b = 1., c = 0., d = 1., e = 0.;
    doFlops(a, b, c, d, e);
  }

  #ifdef USE_MPI
  MPI_Finalize();
  #endif

  return 0;
}
