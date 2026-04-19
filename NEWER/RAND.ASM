;------------------------------------------------------------------------------;
;       random number generator                                                ;
;       8-16-92  Joe Lowe                                                      ;
;------------------------------------------------------------------------------;

_data   segment word public 'data'
_data   ends
_text   segment word public 'code'
_text   ends
assume  cs:_text,ds:_data,es:nothing,ss:nothing



_data   segment

;------------------------------------------------------------------------------;

randseed        dd      0
randmult        dd      0

;------------------------------------------------------------------------------;

_data   ends




_text   segment


;------------------------------------------------------------------------------;
        seed_rand       proc    near
public  seed_rand
;------------------------------------------------------------------------------;
;       initializes random number generator                                    ;
;                                                                              ;
;       call with:                                                             ;
;         ax = seed                                                            ;
;           if ax is zero then system timer is used as seed                    ;
;         ds = data seg                                                        ;
;------------------------------------------------------------------------------;
        push    ax
        push    cx
        push    dx

        mov     cx,ax                   ;copy ax to cx and dx
        mov     dx,ax

        cmp     ax,0                    ;if ax<>0 use it for seed
        jne     sksa

        mov     ah,0                    ;else call bios to get tick count
        int     1ah
sksa:
        or      dx,1                    ;make dx (low word of seed) odd

        mov     word ptr [randseed],dx
        mov     word ptr [randseed+2],cx
        mov     word ptr [randmult],-7
        mov     word ptr [randmult+2],-235

        pop     dx
        pop     cx
        pop     ax
        ret
;------------------------------------------------------------------------------;
seed_rand       endp
;------------------------------------------------------------------------------;






;------------------------------------------------------------------------------;
        random  proc    near
public  random
;------------------------------------------------------------------------------;
;       generates random number                                                ;
;                                                                              ;
;       call with:                                                             ;
;         ax = max value                                                       ;
;         ds = data seg                                                        ;
;       returns:                                                               ;
;         ax = random number                                                   ;
;------------------------------------------------------------------------------;
        push    bx
        push    cx
        push    dx
        push    si

        mov     si,ax                   ;save max val for compare at end

        mov     ax,word ptr [randmult]  ;move mult1 to ax
        mov     cx,ax                   ;copy to cx
        mul     word ptr [randseed]     ;mul mult1 by seed1
        xchg    cx,ax                   ;move low(mult1*seed1) to cx
        mov     bx,dx                   ;move high(mult1*seed1) to bx
        mul     word ptr [randseed+2]   ;mul mult1 by seed2
        add     bx,ax                   ;add low(mult1*seed2) to bx
        mov     ax,word ptr [randmult+2];move mult2 to ax
        mul     word ptr [randseed]     ;mul mult2 to seed1
        add     bx,dx                   ;add low(mult2*seed1) to bx
        mov     word ptr [randseed],cx  ;move l(m1*s1) to seed1
        mov     word ptr [randseed+2],bx;move h(m1*s1)+l(m2*s1)+l(m1*s2)
        mov     ax,bx                   ;    to seed2
        add     word ptr [randmult],2
        adc     word ptr [randmult+2],0

        test    si,si
        jz      rndone
        xor     dx,dx
        div     si
        mov     ax,dx
rndone:
        pop     si
        pop     dx
        pop     cx
        pop     bx
        ret
;------------------------------------------------------------------------------;
random  endp
;------------------------------------------------------------------------------;


_text   ends

end

