import math
import os

os.system('cls')

# Param
Phi_0 = 2067.83


# JoSIM Default Parameter
Ic_Jo = 1000.0
Rn_Jo = 5.0
Cj_Jo = 2.5

# MIT SFQ5ee Default
Ic_MIT = 100.0
Rn_MIT = 16
Cj_MIT = 0.07

# WrSPICE Default Parameter
Ic_WS = 1000.0
Rn_WS = 1.65
Cj_WS = 0.7


######################
# Critical current (uA)
Ic = 77.9
# Parallel Shuted R
R_p = 8
######################

Rn = Rn_MIT #!!!!
KRc = Ic/100
Rn = Rn/KRc
R_real = Rn*R_p/(Rn+R_p)
KR_real = R_real/Rn



Bc_Jo  = 2*math.pi*Ic_Jo*Rn_Jo*Rn_Jo*Cj_Jo/Phi_0
Bc_MIT = 2*math.pi*Ic_MIT*Rn_MIT*Rn_MIT*Cj_MIT/Phi_0
Bc_WS  = 2*math.pi*Ic_WS*Rn_WS*Rn_WS*Cj_WS/Phi_0

Bc_Re = Bc_MIT*KR_real*KR_real

print('***** McCumber Parameter are as: *****\n')
print(f'Bc_Jo:  {Bc_Jo:.2f}')
print(f'Bc_MIT: {Bc_MIT:.2f}')
print(f'Bc_WS:  {Bc_WS:.2f}')

print(f'\nRn = {Rn:.2f} | R_real = {R_real:.2f} | Ic*Rn = {Rn*Ic/1000:.2f}\n')
print('***************************')
print(f'Bc_Re:  {Bc_Re:.2f}')
print('***************************\n')
