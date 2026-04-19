;------------------------------------------------------------------------------;
;       Test program                                                           ;
;       8-16-92  Joe Lowe                                                      ;
;------------------------------------------------------------------------------;

_data   segment word public 'data'
_data   ends

_text   segment word public 'code'
_text   ends

stack_size      equ     2048
_stack  segment word stack 'stack'
stack_buf       db      stack_size dup(?)
_stack  ends

assume  cs:_text,ds:_data,es:nothing,ss:_stack


;------------------------------------------------------------------------------;
extrn   random:near,seed_rand:near
extrn   init_big_mode:near
extrn   term_big_mode:near
extrn   move_window:near
extrn   set_palette:near
extrn   get_palette:near
extrn   plot_pixel:near
extrn   circle:near
;------------------------------------------------------------------------------;



_data   segment


;------------------------------------------------------------------------------;


palette_buf     db      256*2*3 dup(0)
palette_index   dw      0
window_x        dw      0
window_y        dw      0
radius		dw	100
x		dw	160
y		dw	120
color           db      0


;------------------------------------------------------------------------------;


_data   ends





_text   segment


;------------------------------------------------------------------------------;
        main    proc    far
;------------------------------------------------------------------------------;
;------------------------------------------------------------------------------;
        mov     ax,_data
        mov     ds,ax
        mov     ax,_stack
        cli
        mov     ss,ax
        mov     ax,offset stack_buf+stack_size
        mov     sp,ax
        sti

        call    init_big_mode

	mov	ax,0
	int	33h
        mov     bx,offset palette_buf
        call    get_palette
        add     bx,768
        call    get_palette
        mov     bx,offset palette_buf
        mov     cx,256
        mov     dx,offset call_back
        sub     ax,ax
	call	set_palette

        sub     ax,ax
        call    seed_rand

m_loop1:
	mov	bx,[radius]
	inc	bx
	mov	[radius],bx
        mov     al,[color]
        inc     al
        mov     [color],al
        mov     cx,[x]
        mov     dx,[y]
	call	circle
m_skip1:
	mov	ah,1
	int	16h
	jz	m_loop1

	mov	ah,0
	int	16h

        call    term_big_mode

        mov     ax,4c00h
        int     21h
;------------------------------------------------------------------------------;
main    endp
;------------------------------------------------------------------------------;





;------------------------------------------------------------------------------;
        call_back       proc    near
;------------------------------------------------------------------------------;
;       called from palette routines after retrace has occurred                ;
;------------------------------------------------------------------------------;
        push    ax
        push    bx
        push    cx
        push    dx
        push    ds
        mov     ax,_data
        mov     ds,ax

        mov     bx,[palette_index]
        add     bx,3
        cmp     bx,768
        jb      cb_sk1
        sub     bx,bx
cb_sk1:
        mov     [palette_index],bx
        add     bx,offset palette_buf
        mov     cx,256
        mov     dx,offset call_back
        sub     ax,ax
        call    set_palette

        mov     ax,0bh
        int     33h
        add     [window_x],cx
        add     [window_y],dx
        mov     cx,[window_x]
        mov     dx,[window_y]
        call    move_window

        pop     ds
        pop     dx
        pop     cx
        pop     bx
        pop     ax
        ret
;------------------------------------------------------------------------------;
call_back       endp
;------------------------------------------------------------------------------;





_text   ends




end     main





