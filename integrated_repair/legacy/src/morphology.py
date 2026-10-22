"""V11 replaces the blade manifold and plant grammar, not just tessellation.

Procedural world-space metres. Uses the original leaf/damage/attachment pipeline.
No photographic or image-generated content is used by these geometry kernels.
"""
import math, random
from functools import lru_cache
import numpy as np
from mathutils import Vector
import morphology_v9 as M
Z=M.Z; hv=M.hv; unit=M.unit; mix=M.mix; TAU=math.tau
_Base=M.LeafSurface

class AnatomicalBlade(_Base):
    def __init__(self,*a,**k):
        super().__init__(*a,**k)
        self.secondary_phase=0.0
        # Leaf-to-leaf curvature variation, but not independent vertex noise.
        self.rib_strength=.018+.021*(.5+.5*math.sin(self.phase*1.27))
        self.pucker=.45+.55*math.sin(self.phase*.7)**2
    def profile(self,t,v):
        t=max(.0004,min(.9996,float(t)))
        if self.shape=='cordate':
            # Broad shoulders, a cleft around the petiole, and a distinct tip.
            w=math.sin(math.pi*(.07+.93*t))**.65*(1.45-.58*t)
        elif self.shape=='lance': w=math.sin(math.pi*t)**.78*(1.05-.09*t)
        elif self.shape=='pinnule': w=math.sin(math.pi*t)**.72*(1.16-.26*t)
        else:w=math.sin(math.pi*t)**.65*(1.18-.27*t)
        w*=1-.66*M.smoothstep(.86,1,t)
        w*=1+self.asym*math.tanh(v*6)*math.sin(math.pi*t)
        w*=1+.018*math.sin(t*24+self.phase)+.009*math.sin(t*57-self.phase)*math.sin(math.pi*t)
        for center,sign,rad,depth in self.bites:
            if sign*v>0:w*=1-depth*math.exp(-(abs(t-center)/rad)**2.2)
        return w
    def pos(self,t,v):
        t=float(t);v=float(v);av=abs(v);w=self.width*.5*self.profile(t,v)
        lon=t
        if self.shape=='cordate':lon-=.20*math.sin(math.pi*av)**.75*(1-t)**4
        sag=self.length*(.066*math.sin(math.pi*t)-self.droop*t*t-.047*M.smoothstep(.79,1,t)**2)
        phase=(t-.13-.108*av**1.62)/.09125
        # Ribs support curved lamina panels; relief vanishes on the midrib.
        panel=-self.width*self.rib_strength*math.sin(math.pi*phase)**2*math.sin(math.pi*av*.96)
        panel*=.5+.5*math.sin(math.pi*t)**.6
        cup=-self.width*(.025+.06*self.pucker)*math.sin(math.pi*av*.86)*math.sin(math.pi*t)
        curl=self.width*self.curl*.9*av**3*math.sin(math.pi*t)
        twist=self.width*self.twist*1.4*v*t*t
        edge=self.width*.015*math.sin(t*37+self.phase)*av**6*math.sin(math.pi*t)
        lateral=self.width*.04*math.sin(t*math.pi)*math.sin(self.phase+t*4)
        return self.base+self.axis*self.length*lon+self.side*(w*v+lateral)+self.normal*(sag+panel+cup+curl+twist+edge)

@lru_cache(maxsize=8)
def topology(detail):
    nr,nc=(64,22) if detail>=2 else (24,10) if detail else (10,4)
    coords=[(i/nr,-1+2*j/nc) for i in range(nr+1) for j in range(nc+1)]
    faces=[]
    for i in range(nr):
        for j in range(nc):
            a=i*(nc+1)+j;b=a+nc+1;faces.append((a,b,b+1,a+1))
    boundary=list(range(nc+1))+[i*(nc+1)+nc for i in range(1,nr+1)]+[nr*(nc+1)+j for j in range(nc-1,-1,-1)]+[i*(nc+1) for i in range(nr-1,0,-1)]
    return coords,faces,boundary

def install():
    M.LeafSurface=AnatomicalBlade;M.regular_topology=topology


def petiole_leaf(mesh,rng,root,direction,L,width,age=.6,detail=1,shape='elliptic',roll=0):
    d=unit(direction);side=unit(d.cross(Z),(0,1,0))
    normal=unit(Z+side*roll)
    tip=Vector(root)+d*L*.18+Z*L*.025
    mesh.tube([root,Vector(root).lerp(tip,.52)+Z*L*.013,tip],[L*.014,L*.008,L*.0032],'stem',6,(.044,.071,.018))
    M.leaf(mesh,rng,tip,d,normal,L,width,shape,detail,age,damage=.18)
    mesh.counts['integrated_petiole_blades']+=1


def compound_shoot(mesh,rng,start,direction,length,variant,detail=0):
    """A foliated shoot with real rachis or terminal twigs, chosen by family."""
    d=unit(direction);side=unit(d.cross(Z),(0,1,0));base=Vector(start)
    end=base+d*length+Z*length*rng.uniform(-.12,.15)
    ctrl=[base,base+d*length*.26+Z*.025,base.lerp(end,.70)+side*length*.12,end]
    pts=[M.bezier(*ctrl,t) for t in np.linspace(0,1,16)]
    mesh.tube(pts,[max(.00045,length*.014*(1-.96*t)) for t in np.linspace(0,1,16)],'stem',6,(.055,.043,.026))
    pairs=rng.randint(5,8) if variant%4==1 else rng.randint(3,6)
    for k in range(pairs):
        t=.14+.78*(k+.2)/pairs;p=M.bezier(*ctrl,t)
        signs=(-1,1) if variant%4 in (1,3) else ((-1 if k%2 else 1),)
        for sign in signs:
            direction=unit(d*.45+side*sign+Z*rng.uniform(-.27,.31))
            L=rng.uniform(.105,.20)*(1-.22*t)
            if variant%4==1:
                M.leaf(mesh,rng,p,direction,Z,L,L*.35,'lance',detail,rng.uniform(.35,.8),damage=.07,veins=detail>0)
            else:
                petiole_leaf(mesh,rng,p,direction,L,L*(.58 if variant%4==0 else .42),rng.uniform(.28,.87),detail,roll=rng.uniform(-.35,.35))
    petiole_leaf(mesh,rng,end,d+Z*.2,.047,.018,.12,0,'lance')
    mesh.counts['distinct_family_shoots']+=1


def architectural_tree(mesh,seed,H,R,variant=0):
    """Non-tiered, asymmetric branching from lower stem into lateral crowns.

    Different families: compound leaves, irregular broadleaf branches, bowed
    understory leaders and forked fan crowns. No identical level/arm scaffolds.
    """
    rng=random.Random(seed);ph=rng.random()*TAU
    lean=hv(ph)*H*rng.uniform(.09,.17);kink=hv(ph+1.8)*H*rng.uniform(.025,.055)
    def trunk(t):return Z*H*t+lean*t*t+kink*math.sin(math.pi*t)
    rad=H*rng.uniform(.008,.014)
    ts=np.linspace(0,1,42)
    mesh.tube([trunk(t) for t in ts],[max(.0014,rad*(1-.983*t)**1.1) for t in ts],'stem',12,(.055,.046,.028))
    branch_levels=sorted(rng.uniform(.19,.96) for _ in range(rng.randint(12,18)))
    for k,t in enumerate(branch_levels):
        p=trunk(t);a=ph+k*2.399963+rng.gauss(0,.8);d=hv(a)
        lng=min(R*1.2,H*.46)*rng.uniform(.6,1.15)*(1-.44*t)
        rise=H*rng.uniform(-.036,.07) if variant%3 else H*rng.uniform(.05,.12)
        end=p+d*lng+Z*rise
        ctrl=[p,p+d*lng*.28+Z*abs(rise)*.7,p+d*lng*.72+Z*rise+Z*lng*.1,end-Z*lng*.08]
        ps=[M.bezier(*ctrl,u) for u in np.linspace(0,1,20)]
        r=rad*rng.uniform(.25,.48)*(1-.42*t)
        mesh.tube(ps,[max(.001,r*(1-u*.96)) for u in np.linspace(0,1,20)],'stem',8,(.051,.04,.024))
        M.collar(mesh,p,d+Z*.2,r,rng)
        for j in range(rng.randint(4,7)):
            u=rng.uniform(.28,.99);q=M.bezier(*ctrl,u);sg=1 if j%2 else -1
            ax=unit(d*.24+hv(a+sg*rng.uniform(.65,1.5))+Z*rng.uniform(-.18,.35))
            compound_shoot(mesh,rng,q,ax,rng.uniform(.28,.55),variant,0)
        mesh.counts['non_tiered_primary_branches']+=1
    # Two subordinate leaders begin at actual forks, not a second floating tree.
    for j in range(1+(variant%3==0)):
        t=.24+.20*j;root=trunk(t);d=hv(ph+1.7+j*2.1);length=H*rng.uniform(.35,.55)
        end=root+Z*length+d*H*.17;ctrl=[root,root+Z*length*.36+d*length*.3,end-Z*length*.3,end]
        ts=np.linspace(0,1,26)
        mesh.tube([M.bezier(*ctrl,u) for u in ts],[max(.001,rad*.58*(1-.97*u)) for u in ts],'stem',10,(.055,.046,.028))
        for k in range(8):
            u=.17+.79*k/8;q=M.bezier(*ctrl,u);ax=unit(hv(ph+k*2.399+j)+Z*.16)
            compound_shoot(mesh,rng,q,ax,rng.uniform(.35,.65),variant+1,0)
        mesh.counts['rooted_subordinate_leaders']+=1


def understory(mesh,seed,H,variant=0):
    rng=random.Random(seed);ph=rng.random()*TAU
    for s in range(2+(variant%3)):
        h=H*rng.uniform(.55,1.0);a=ph+s*2.399;d=hv(a)
        root=d*.018;end=Z*h+d*h*.22;ctrl=[root,root+Z*h*.35,end-Z*h*.28,end]
        ts=np.linspace(0,1,24)
        mesh.tube([M.bezier(*ctrl,t) for t in ts],[max(.0007,h*.01*(1-.92*t)) for t in ts],'stem',9,(.054,.048,.027))
        for j in range(6+(variant%3)):
            t=.20+.74*j/(6+variant%3);p=M.bezier(*ctrl,t);dr=unit(hv(a+j*2.399)+Z*rng.uniform(-.22,.3))
            compound_shoot(mesh,rng,p,dr,h*rng.uniform(.20,.38),variant,1)
        mesh.counts['foliated_juvenile_leaders']+=1


def ground_broadleaf(mesh,seed,H,variant=0):
    rng=random.Random(seed);ph=rng.random()*TAU
    # Multiple ages; some unfolded, some fully open, one senescent sheath.
    for k in range(rng.randint(11,16)):
        a=ph+k*2.39996+rng.gauss(0,.17);d=hv(a);age=.18+.72*k/15
        root=d*.025;end=d*H*rng.uniform(.22,.49)+Z*H*rng.uniform(.45,.92)*(1-.27*age)
        ctrl=[root,root+Z*H*.3,end-Z*H*.12,end]
        pts=[M.bezier(*ctrl,t) for t in np.linspace(0,1,22)]
        mesh.tube(pts,[H*.006*(1-.61*t) for t in np.linspace(0,1,22)],'stem',9,(.04,.073,.02))
        L=H*rng.uniform(.30,.44);L=min(L,.53)
        shape=('cordate','elliptic','lance','elliptic')[variant%4]
        M.leaf(mesh,rng,end,unit(d+Z*rng.uniform(-.3,.24)),unit(Z+hv(a+1.6)*rng.uniform(-.2,.2)),L,L*(.70 if shape=='cordate' else .39 if shape=='lance' else .55),shape,2,age,damage=.22)
        mesh.counts['differentiated_basal_leaves']+=1
        if k%5==0:M.leaf(mesh,rng,root,unit(Z+d*.5),d,H*.16,H*.032,'lance',1,.93,True,.4)
