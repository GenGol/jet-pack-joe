;------------------------------------------------------------------------------;
;       Big Mode (vga 512x512 in 320x240 window)                               ;
;       8-26-92  Joe Lowe                                                      ;
;------------------------------------------------------------------------------;
        .186

_text   segment word public 'code'
_text   ends
assume  cs:_text,ds:_text,es:nothing,ss:nothing


video_seg       equ     0a000h



_text   segment

;------------------------------------------------------------------------------;

old_mode        db      0

;------------------------------------------------------------------------------;


;------------------------------------------------------------------------------;
	_InitBigMode	proc	near
public	_InitBigMode
;------------------------------------------------------------------------------;
;       puts vga adapter in 320x240 256 color graphics mode                    ;
;       lengthens retrace to reduce flicker on palette loads                   ;
;       with 512 pixels per logical line                                       ;
;------------------------------------------------------------------------------;
init_big_mode	label	near
public	init_big_mode
        push    ax
        push    dx
        pushf
        cli

        mov     ah,0fh
        int     10h
        mov     [cs:old_mode],al

        mov     ax,13h                  ;set mode 13h to get palette
        int     10h                     ;
        mov     ax,1201h                ;disable palette loading on mode change
        mov     bl,31h                  ;
        int     10h                     ;

        mov     ax,92h          ;let bios put adapter in 640x480 16 color mode
        int     10h             ;

        mov     dx,3c6h         ;open all bits in dac mask
        mov     al,0ffh         ;
        out     dx,al           ;

        mov     dx,3d4h         ;set max scan line to 1 (2 scan high pixels)
        mov     al,9            ;
        out     dx,al           ;
        inc     dx              ;
        in      al,dx           ;
        or      al,1            ;
        out     dx,al           ;

        mov     dx,3ceh         ;set 256 color mode in graphics mode register
        mov     al,5            ;
        out     dx,al           ;
        inc     dx              ;
        in      al,dx           ;
        or      al,40h          ;
        out     dx,al           ;

        mov     dx,3dah         ;set 256 color mode in attribute mode register
        in      al,dx           ;
        mov     dx,3c0h         ;
        mov     al,10h          ;  (notice how much more shit you have to go
        out     dx,al           ;   through to read/write an attribute register)
        inc     dx              ;
        in      al,dx           ;
        or      al,60h          ;
        mov     ah,al           ;
        mov     dx,3dah         ;-these two lines may not be necessary but better
        in      al,dx           ;-safe than sorry
        mov     dx,3c0h         ;
        mov     al,10h          ;
        out     dx,al           ;
        mov     al,ah           ;
        out     dx,al           ;
        mov     al,20h          ;
        out     dx,al           ;

        mov     dx,3d4h         ;remaining writes are all to crtc registers

        mov     al,10h          ;start vertical retrace 7 scan lines sooner
        out     dx,al           ;
        inc     dx              ;
        in      al,dx           ;
        sub     al,7            ;
        out     dx,al           ;
        dec     dx              ;

        mov     al,11h          ;end vertical retrace 7 scan lines later
        out     dx,al           ;
        inc     dx              ;
        in      al,dx           ;
        add     al,7            ;
        out     dx,al           ;
        dec     dx              ;

        mov     al,15h          ;start vertical blanking 7 scan lines sooner
        out     dx,al           ;
        inc     dx              ;
        in      al,dx           ;
        sub     al,7            ;
        out     dx,al           ;
        dec     dx              ;

        mov     al,16h          ;end vertical retrace 7 scan lines later
        out     dx,al           ;
        inc     dx              ;
        in      al,dx           ;
        add     al,7            ;
        out     dx,al           ;
        dec     dx              ;

        mov     dx,3d4h         ;set offset register
        mov     cl,7            ;
        mov     ax,4013h        ;
        out     dx,ax           ;

	mov	ax,0101h
        call    clear_video

        popf
	call	init_retrace

        pop     dx
        pop     ax
        ret
;------------------------------------------------------------------------------;
_InitBigMode	endp
;------------------------------------------------------------------------------;








;------------------------------------------------------------------------------;
        move_window     proc    near
public  move_window
;------------------------------------------------------------------------------;
;       sets starting dislay offset and horizontal smooth scroll registers     ;
;       for 256 color graphics modes                                           ;
;                                                                              ;
;       call with:                                                             ;
;         cx,dx = x,y coordinate of top of window                              ;
;------------------------------------------------------------------------------;
        push    ax
        push    dx

        mov     ax,cx
        and     al,3
        shl     al,1
        mov     [cs:pixel_pan],al
        mov     ax,cx
        shr     ax,2
        and     ax,07fh
        shl     dx,7
        add     ax,dx
        mov     [cs:start_offset],ax

        pop     dx
        pop     ax
        ret
;------------------------------------------------------------------------------;
move_window     endp
;------------------------------------------------------------------------------;







;------------------------------------------------------------------------------;
	_TermBigMode	proc	near
public	_TermBigMode
;------------------------------------------------------------------------------;
;       terminates big graphics mode                                           ;
;------------------------------------------------------------------------------;
term_big_mode	label	near
public	term_big_mode
        push    ax
	call	term_retrace
        mov     ax,1200h                ;reenable palette loading on mode change
        mov     bl,31h                  ;
        int     10h                     ;
        mov     al,[cs:old_mode]
        and     ax,07fh
        int     10h
        pop     ax
        ret
;------------------------------------------------------------------------------;
_TermBigMode	endp
;------------------------------------------------------------------------------;






;------------------------------------------------------------------------------;
        clear_video     proc    near
public  clear_video
;------------------------------------------------------------------------------;
;       clear all of video memory                                              ;
;                                                                              ;
;       call with:                                                             ;
;         al = color to fill video memory with                                 ;
;------------------------------------------------------------------------------;
        push    ax
        push    cx
        push    dx
        push    di
        push    es

        mov     cl,al
        mov     ch,al

        mov     ax,0f02h                ;mask and port number of plane mask reg
        mov     dx,3c4h                 ;port address of plane mask
        out     dx,ax                   ;set mask

        mov     ax,video_seg
        mov     es,ax
        sub     di,di
        mov     ax,8000h
        xchg    ax,cx
        rep     stosw

        pop     es
        pop     di
        pop     dx
        pop     cx
        pop     ax
        ret
;------------------------------------------------------------------------------;
clear_video     endp
;------------------------------------------------------------------------------;









;------------------------------------------------------------------------------;
	plot_pixel	proc	near
public	plot_pixel
;------------------------------------------------------------------------------;
;       plot point on screen                                                   ;
;                                                                              ;
;       call with:                                                             ;
;         al = color                                                           ;
;         cx,dx = x,y coordinate on screen                                     ;
;         ds = data seg                                                        ;
;------------------------------------------------------------------------------;
        push    ax
        push    bx
        push    cx
        push    dx
        push    es
        mov     bx,video_seg
        mov     es,bx

        and     ch,1
        and     dh,1
        mov     bx,cx                   ;copy x coord to bx
        sar     bx,2                    ;div x by 4
        mov     ch,al                   ;copy color to ch
        shl     dx,7                    ;128 bytes per row on screen
        add     bx,dx                   ;address in bx=x/4+y
        and     cl,3                    ;cl shift for plane mask

        mov     ax,0102h                ;mask and port number of plane mask reg
        shl     ah,cl                   ;shift mask with x mod 4
        mov     dx,3c4h                 ;port address of plane mask
        out     dx,ax                   ;set mask

        mov     es:[bx],ch              ;write point

        pop     es
        pop     dx
        pop     cx
        pop     bx
        pop     ax
        ret
;------------------------------------------------------------------------------;
plot_pixel	endp
;------------------------------------------------------------------------------;








;------------------------------------------------------------------------------;
	offset_mask	 proc	 near
public	offset_mask
;------------------------------------------------------------------------------;
;       plot point on screen                                                   ;
;                                                                              ;
;       call with:                                                             ;
;         cx,dx = x,y coordinate on screen                                     ;
;	returns:							       ;
;	  ax = mask in ah with index in al				       ;
;	  bx = offset in video buffer					       ;
;------------------------------------------------------------------------------;
        push    cx
        mov     bx,cx                   ;copy x coord to bx
        sar     bx,2                    ;div x by 4
        shl     dx,7                    ;128 bytes per row on screen
        add     bx,dx                   ;address in bx=x/4+y
        and     cl,3                    ;cl shift for plane mask
	mov	ax,1102h		;mask and port number of plane mask reg
        shl     ah,cl                   ;shift mask with x mod 4
        pop     cx
        ret
;------------------------------------------------------------------------------;
offset_mask	 endp
;------------------------------------------------------------------------------;








;------------------------------------------------------------------------------;
        circle  proc    near
public  circle
;------------------------------------------------------------------------------;
;       draws circle                                                           ;
;                                                                              ;
;       call with:                                                             ;
;         al = color                                                           ;
;         bx = radius                                                          ;
;         cx,dx = x,y coordinate of center                                     ;
;------------------------------------------------------------------------------;
        push    bp
        mov     bp,sp

center_x        equ     word ptr [bp-2]
center_y        equ     word ptr [bp-4]
delta_x         equ     word ptr [bp-6]
delta_y         equ     word ptr [bp-8]
decision        equ     word ptr [bp-10]
radius          equ     word ptr [bp-12]
color           equ     word ptr [bp-14]
pixel1_offset	equ	word ptr [bp-16]
pixel2_offset	equ	word ptr [bp-18]
pixel3_offset	equ	word ptr [bp-20]
pixel4_offset	equ	word ptr [bp-22]
pixel1_mask	equ	word ptr [bp-24]
pixel2_mask	equ	word ptr [bp-26]
pixel3_mask	equ	word ptr [bp-28]
pixel4_mask	equ	word ptr [bp-30]

	sub	sp,30

        pusha
	push	ds
	mov	si,video_seg
	mov	ds,si

        mov     [color],ax
        mov     [radius],bx
        mov     [delta_x],bx
        neg     bx
        mov     [decision],bx
        mov     [delta_y],0
        mov     [center_x],cx
        mov     [center_y],dx

        mov     cx,[center_x]
        mov     dx,[center_y]
        add     cx,[delta_x]
        add     dx,[delta_y]
	call	offset_mask
	mov	[pixel1_offset],bx
	mov	[pixel1_mask],ax
	mov	cx,[center_x]
        mov     dx,[center_y]
        sub     cx,[delta_x]
        sub     dx,[delta_y]
	call	offset_mask
	mov	[pixel2_offset],bx
	mov	[pixel2_mask],ax
        mov     cx,[center_x]
        mov     dx,[center_y]
        sub     cx,[delta_x]
        add     dx,[delta_y]
	call	offset_mask
	mov	[pixel3_offset],bx
	mov	[pixel3_mask],ax
        mov     cx,[center_x]
        mov     dx,[center_y]
        add     cx,[delta_x]
        sub     dx,[delta_y]
	call	offset_mask
	mov	[pixel4_offset],bx
	mov	[pixel4_mask],ax

	mov	dx,3c4h
c1_loop:
	mov	cx,[color]
	mov	ax,[pixel1_mask]
	mov	bx,[pixel1_offset]
	out	dx,ax
	mov	[ds:bx],cl
	mov	ax,[pixel2_mask]
	mov	bx,[pixel2_offset]
	out	dx,ax
	mov	[ds:bx],cl
	mov	ax,[pixel3_mask]
	mov	bx,[pixel3_offset]
	out	dx,ax
	mov	[ds:bx],cl
	mov	ax,[pixel4_mask]
	mov	bx,[pixel4_offset]
	out	dx,ax
	mov	[ds:bx],cl

	cmp	[decision],0
        jge     c1_left
c1_up:
        mov     ax,[delta_y]
        add     [decision],ax
        inc     [delta_y]
	add	[pixel1_offset],128
	add	[pixel3_offset],128
	sub	[pixel2_offset],128
	sub	[pixel4_offset],128
        jmp     c1_loop
c1_left:
        mov     ax,[delta_x]
        sub     [decision],ax
	ror	[byte ptr pixel1_mask+1],1
	sbb	[pixel1_offset],0
	ror	[byte ptr pixel4_mask+1],1
	sbb	[pixel4_offset],0
	rol	[byte ptr pixel2_mask+1],1
	adc	[pixel2_offset],0
	rol	[byte ptr pixel3_mask+1],1
	adc	[pixel3_offset],0
        dec     [delta_x]
        jge     c1_loop

	pop	ds
	popa
        mov     sp,bp
        pop     bp
        ret
;------------------------------------------------------------------------------;
circle  endp
;------------------------------------------------------------------------------;


if 0
center_x	dw	0
center_y	dw	0
delta_x 	dw	0
delta_y 	dw	0
decision	dd	0
dec_x		dd	0
dec_y		dd	0
color		db	0
x_rad		dw	0
y_rad		dw	0
endif



;------------------------------------------------------------------------------;
	elipse	proc	near
public	elipse
;------------------------------------------------------------------------------;
;	draws elipse							       ;
;                                                                              ;
;       call with:                                                             ;
;         al = color                                                           ;
;	  si,di = x,y radius						       ;
;         cx,dx = x,y coordinate of center                                     ;
;------------------------------------------------------------------------------;
        push    bp
        mov     bp,sp
center_x        equ     word ptr [bp-2]
center_y        equ     word ptr [bp-4]
delta_x         equ     word ptr [bp-6]
delta_y         equ     word ptr [bp-8]
decision	equ	dword ptr [bp-12]
dec_x		equ	dword ptr [bp-16]
dec_y		equ	dword ptr [bp-20]
color		equ	byte ptr [bp-22]
x_rad		equ	word ptr [bp-24]
y_rad		equ	word ptr [bp-26]
	sub	sp,26

        pusha
	push	ds
	mov	bx,cs
	mov	ds,bx

	mov	[color],al
        mov     [center_x],cx
        mov     [center_y],dx
	mov	[x_rad],si
	mov	[y_rad],di
	mov	[delta_x],si
        mov     [delta_y],0
	mov	ax,si
	mul	di
	mov	[word ptr dec_x],ax
	mov	[word ptr dec_x+2],dx
	mov	[word ptr decision],0
	mov	[word ptr decision+2],0
	mov	[word ptr dec_y],0
	mov	[word ptr dec_y+2],0

e1_loop:
	mov	al,[color]
        mov     cx,[center_x]
        mov     dx,[center_y]
        add     cx,[delta_x]
        add     dx,[delta_y]
        call    plot_pixel
        mov     cx,[center_x]
        mov     dx,[center_y]
        sub     cx,[delta_x]
        sub     dx,[delta_y]
        call    plot_pixel
        mov     cx,[center_x]
        mov     dx,[center_y]
        sub     cx,[delta_x]
        add     dx,[delta_y]
        call    plot_pixel
        mov     cx,[center_x]
        mov     dx,[center_y]
        add     cx,[delta_x]
        sub     dx,[delta_y]
        call    plot_pixel

	cmp	[word ptr decision+2],0
	jl	e1_left
e1_up:
	mov	ax,[word ptr dec_y]
	mov	dx,[word ptr dec_y+2]
	sub	[word ptr decision],ax
	sbb	[word ptr decision+2],dx
	add	ax,[x_rad]
	adc	dx,0
	mov	[word ptr dec_y],ax
	mov	[word ptr dec_y+2],dx
        inc     [delta_y]
	jmp	e1_loop
e1_left:
	mov	ax,[word ptr dec_x]
	mov	dx,[word ptr dec_x+2]
	add	[word ptr decision],ax
	adc	[word ptr decision+2],dx
	sub	ax,[y_rad]
	sbb	dx,0
	mov	[word ptr dec_x],ax
	mov	[word ptr dec_x+2],dx
        dec     [delta_x]
	jl	e1_done
	jmp	e1_loop

e1_done:
	pop	ds
	popa
        mov     sp,bp
        pop     bp
        ret
;------------------------------------------------------------------------------;
elipse	endp
;------------------------------------------------------------------------------;





















;------------------------------------------------------------------------------;



interrupt_delay equ     1024            ;these two number multiplied should equal
chain_delay     equ     64              ;  65536

align   2

ticks_between   dw      0
vector_08h      dd      handler_08h
count_down      dw      0
chain_count     dw      chain_delay
start_offset    dw      0
pixel_pan       db      0
first_dac       db      0
number_dacs     dw      0
dac_data_ptr    dd      0
call_back       dw      -1

;------------------------------------------------------------------------------;







;------------------------------------------------------------------------------;
        init_retrace    proc    near
;------------------------------------------------------------------------------;
;       initializes interrupt driven retrace polling routines                  ;
;------------------------------------------------------------------------------;
        push    ax
        push    bx
        push    ds
        mov     ax,cs
        mov     ds,ax

        mov     [count_down],65535
        mov     [ticks_between],10000

        mov     ax,8                            ;swap new int 8 vector with old
        mov     bx,offset vector_08h            ;
        call    swap_int_vector                 ;

        mov     al,36h                          ;set new tick speed
        out     43h,al                          ;
        mov     ax,interrupt_delay              ;
        out     40h,al                          ;
        mov     al,ah                           ;
        out     40h,al                          ;

        mov     dx,03dah
ir_loop1:
ir_wait1:
        in      al,dx                           ;wait for retrace to end
        test    al,8                            ;
        jnz     ir_wait1                        ;
ir_wait2:
        in      al,dx                           ;wait for retrace to start again
        test    al,8                            ;
        jz      ir_wait2                        ;

        mov     bx,[count_down]                 ;save current value of count down
ir_wait3:
        in      al,dx                           ;wait for retrace to end
        test    al,8                            ;
        jnz     ir_wait3                        ;
ir_wait4:
        in      al,dx                           ;wait for retrace to start again
        test    al,8                            ;
        jz      ir_wait4                        ;

        sub     bx,[count_down]                 ;calculate number of interrupts
                                                ;  between retraces
        cmp     bx,[ticks_between]              ;if between ticks less than or same as
        ja      ir_out1                         ;  previous then replace and time again
        mov     [ticks_between],bx              ;if greater than previous then we've
        jmp     ir_loop1                        ;  found the shortest gap
ir_out1:
        mov     ax,[ticks_between]              ;setup poll interrupt for next retrace
        mov     [count_down],ax                 ;

        pop     ds
        pop     bx
        pop     ax
        ret
;------------------------------------------------------------------------------;
init_retrace    endp
;------------------------------------------------------------------------------;







;------------------------------------------------------------------------------;
        term_retrace    proc    near
;------------------------------------------------------------------------------;
;       deinstalls retrace poller                                              ;
;------------------------------------------------------------------------------;
        push    ax
        push    bx
        push    ds
        mov     ax,cs
        mov     ds,ax

        mov     al,36h                          ;reset default tick speed
        out     43h,al                          ;
        sub     al,al                           ;put zeros in count (65535)
        out     40h,al                          ;
        out     40h,al                          ;

        mov     ax,8                            ;swap new int 8 vector with old
        mov     bx,offset vector_08h            ;
        call    swap_int_vector                 ;

        pop     ds
        pop     bx
        pop     ax
        ret
;------------------------------------------------------------------------------;
term_retrace    endp
;------------------------------------------------------------------------------;








;------------------------------------------------------------------------------;
        swap_int_vector proc    near
;------------------------------------------------------------------------------;
;       call with:                                                             ;
;         ax = interrput number                                                ;
;         [ds:bx] = pointer to vector to swap with                             ;
;------------------------------------------------------------------------------;
        push    ax
        push    cx
        push    si
        push    es

        shl     ax,1
        shl     ax,1
        mov     si,ax

        sub     cx,cx
        mov     es,cx

        mov     ax,[es:si]
        mov     cx,[es:si+2]
        xchg    ax,[ds:bx]
        xchg    cx,[ds:bx+2]
        cli
        mov     [es:si],ax
        mov     [es:si+2],cx
        sti

        pop     es
        pop     si
        pop     cx
        pop     ax
        ret
;------------------------------------------------------------------------------;
swap_int_vector endp
;------------------------------------------------------------------------------;






;------------------------------------------------------------------------------;
        handler_08h     proc    far
;------------------------------------------------------------------------------;
;       catches accelerated timer tick interrupt and calls retrace handler     ;
;         after [ticks_between] times                                          ;
;       chains to old vector 18 times per second                               ;
;------------------------------------------------------------------------------;
        push    ax

        mov     al,20h
        out     20h,al
        sti

        dec     [cs:count_down]
        jz      h08_do1

        dec     [cs:chain_count]
        jz      h08_chain

        pop     ax
        iret

h08_do1:
        push    dx

        mov     dx,03dah                        ;wait until retrace starts
h08_wait1:                                      ;
        in      al,dx                           ;
        test    al,8                            ;
        jz      h08_wait1                       ;

        mov     ax,[cs:ticks_between]
        mov     [cs:count_down],ax

        mov     dx,3d4h         ;next writes are to crtc registers
        mov     al,0ch          ;set start offset
        mov     ah,[byte ptr cs:start_offset+1]
        out     dx,ax           ;
        inc     al              ;
        mov     ah,[byte ptr cs:start_offset]
        out     dx,ax           ;

        mov     dx,3dah         ;set horizontal pixel pan register
        in      al,dx           ;
        mov     dx,3c0h         ;
        mov     al,13h          ;
        out     dx,al           ;
        mov     al,[cs:pixel_pan]
        out     dx,al           ;
        mov     al,20h          ;
        out     dx,al           ;

        cmp     [cs:number_dacs],0
        je      h08_dodone

        push    cx                      ;
        push    si                      ;
        push    ds                      ;

        lds     si,[cs:dac_data_ptr]    ;load palette registers
        mov     dx,3c8h                 ;
        mov     al,[cs:first_dac]       ;
        out     dx,al                   ;
        inc     dx                      ;
        sub     cx,cx                   ;
        xchg    cx,[cs:number_dacs]     ;
        rep     outsb                   ;

        mov     ax,[cs:call_back]       ;if callback offset not -1 then call it
        cmp     ax,-1                   ;
        je      h08_sk1                 ;
        call    [cs:call_back]          ;
h08_sk1:                                ;
        pop     ds                      ;
        pop     si                      ;
        pop     cx                      ;

h08_dodone:
        pop     dx

        dec     [cs:chain_count]
        jz      h08_chain

        pop     ax
        iret

h08_chain:
        mov     [cs:chain_count],chain_delay
        pushf
        call    [cs:vector_08h]
        pop     ax
        iret
;------------------------------------------------------------------------------;
handler_08h     endp
;------------------------------------------------------------------------------;






;------------------------------------------------------------------------------;
        set_palette     proc    near
public  set_palette
;------------------------------------------------------------------------------;
;       writes 768 byte to palette                                             ;
;                                                                              ;
;       call with:                                                             ;
;         ax = first dac register to load                                      ;
;         [ds:bx] = buffer containing palette data                             ;
;         cx = number of dac registers to load                                 ;
;         [cs:dx] = near routine to be called after palette load is finished   ;
;           dx = -1 then no call back will be made                             ;
;------------------------------------------------------------------------------;
        push    ax
        mov     [cs:first_dac],al
        mov     ax,cx
        shl     ax,1
        add     ax,cx
        mov     [cs:number_dacs],ax
        mov     [word ptr cs:dac_data_ptr],bx
        mov     [word ptr cs:dac_data_ptr+2],ds
        mov     [cs:call_back],dx
        pop     ax
        ret
;------------------------------------------------------------------------------;
set_palette     endp
;------------------------------------------------------------------------------;






;------------------------------------------------------------------------------;
        get_palette     proc    near
public  get_palette
;------------------------------------------------------------------------------;
;       reads 768 byte to palette                                              ;
;                                                                              ;
;       call with:                                                             ;
;         [ds:bx] = buffer to recieve 768 byte of palette information          ;
;------------------------------------------------------------------------------;
        push    ax
        push    cx
        push    dx
        push    di
        push    es
        mov     ax,ds
        mov     es,ax

        mov     di,bx

        mov     dx,3c3h
        sub     al,al
        out     dx,al
        mov     dx,3c7h
        sub     al,al
        out     dx,al
        add     dx,2
        mov     cx,768
        rep     insb
        mov     dx,3c3h
        mov     al,1
        out     dx,al

        pop     es
        pop     di
        pop     dx
        pop     cx
        pop     ax
        ret
;------------------------------------------------------------------------------;
get_palette     endp
;------------------------------------------------------------------------------;















_text   ends




end
