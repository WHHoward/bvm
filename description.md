总共有N1~N8八个节点
从左至右为S-Loop和R-Loop
S-Loop包含N1\N2\N5三个节点
N1位于S-Loop的左上角,N1左接BL，N1上接WL，N1右边依次连接LM2->JM2->N2,N1下接JM1->LM1->GND
N2左边连接的JM2,N2下面接的是LM3->N5,N2右边接的依次是LS1->JS1->N3
R-Loop包含N2\N5\N3\N4\N6\N7
N3上接SE,左接JS1,右边直接与N4相连,下面连接RS->N6
N4位于R-Loop右上角,左边连接的N3,下面连接的LS3->N7
N5上接LM3,右接LS2->JS2->N6,下接LPM->GND
N6上接RS,左接JS2，右边直接与N7相连
N7上接LS3,左边直接与N6相连,右边连接LPSL->RSL->N8
N8左边与RSL连接,上接SL,下接LSL->DataOut
S-Loop与R-Loop共享N2-LM3-N5

N1左边连接LPRBL->RBL->BL
N1上面连接LPRWL->RWL->WL
N3上面连接LPRSE->RSE->SE

