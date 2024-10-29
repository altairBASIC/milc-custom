# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, undefined-variable, used-before-assignment
# pylama: ignore=E0602

gpu_arch = USERARG.get('GPU_ARCH', 'sm_60')

# Importar modulos HPCCM
from hpccm.building_blocks import *
from hpccm.primitives import *

# Etapa de construccion del contenedor
Stage0 += baseimage(image='nvcr.io/nvidia/nvhpc:20.7-devel-centos7', _as='build')

# Instalacion de dependencias necesarias
Stage0 += shell(commands=[
    'yum install -y make gcc gcc-c++ wget && rm -rf /var/cache/yum/*',
    'wget https://cmake.org/files/v3.18/cmake-3.18.0.tar.gz && \
     tar -zxvf cmake-3.18.0.tar.gz && \
     cd cmake-3.18.0 && \
     ./bootstrap && \
     make && \
     make install && \
     cd .. && rm -rf cmake-3.18.0 cmake-3.18.0.tar.gz'
])

# Definición de comandos para QUDA
quda_commands = '''
    mkdir -p /var/tmp && cd /var/tmp && git clone --depth=1 --branch develop https://github.com/lattice/quda.git quda && cd - && 
    cd /var/tmp/quda && 
    mkdir -p /usr/local/quda && 
    mkdir -p /var/tmp/quda/build && cd /var/tmp/quda/build && 
    cmake -DCMAKE_INSTALL_PREFIX=/usr/local/quda -D CMAKE_BUILD_TYPE=RELEASE -D QUDA_DIRAC_CLOVER=ON -D QUDA_DIRAC_DOMAIN_WALL=ON -D QUDA_DIRAC_STAGGERED=ON -D QUDA_DIRAC_TWISTED_CLOVER=ON -D QUDA_DIRAC_TWISTED_MASS=ON -D QUDA_DIRAC_WILSON=ON -D QUDA_FORCE_GAUGE=ON -D QUDA_FORCE_HISQ=ON -D QUDA_GPU_ARCH={} -D QUDA_INTERFACE_MILC=ON -D QUDA_INTERFACE_QDP=ON -D QUDA_LINK_HISQ=ON -D QUDA_MPI=ON /var/tmp/quda && 
    cmake --build . --target all -- -j$(nproc) && 
    cd /usr/local/quda && cp -a /var/tmp/quda/build/* /usr/local/quda && 
    echo "/usr/local/quda/lib" >> /etc/ld.so.conf.d/hpccm.conf && ldconfig && rm -rf /var/tmp/quda
'''.format(gpu_arch)

# Clonacion del repositorio QUDA
Stage0 += shell(commands=[quda_commands])

# Construccion de MILC
Stage0 += generic_build(branch='develop',
                        build=['cp Makefile ks_imp_rhmc',
                               'cd ks_imp_rhmc',
                               'make -j 1 su3_rhmd_hisq \
                                CC=/usr/local/openmpi/bin/mpicc \
                                LD=/usr/local/openmpi/bin/mpicxx \
                                QUDA_HOME=/usr/local/quda \
                                WANTQUDA=true \
                                WANT_GPU=true \
                                WANT_CL_BCG_GPU=true \
                                WANT_FN_CG_GPU=true \
                                WANT_FL_GPU=true \
                                WANT_FF_GPU=true \
                                WANT_GF_GPU=true \
                                MPP=true \
                                PRECISION=2 \
                                WANTQIO=""'],
                        install=['mkdir -p /usr/local/milc/bin',
                                 'cp /var/tmp/milc_qcd/ks_imp_rhmc/su3_rhmd_hisq /usr/local/milc/bin'],
                        prefix='/usr/local/milc',
                        repository='https://github.com/milc-qcd/milc_qcd')

# Definicion de la imagen de tiempo de ejecucion
Stage1 += baseimage(image='nvcr.io/nvidia/nvhpc:20.7-runtime-cuda10.1-centos7')

# Copia del binario compilado a la imagen de tiempo de ejecucion
Stage1 += copy(src='/usr/local/quda', dest='/usr/local/quda')
Stage1 += copy(src='/usr/local/milc/bin', dest='/usr/local/milc/bin')

# Configuracion de variables de entorno
Stage1 += environment(variables={'PATH': '/usr/local/quda/bin:/usr/local/milc/bin:$PATH'})
