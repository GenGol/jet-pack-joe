
;------------------------------------------------------------------------------;
;spawn multi-edit demo program and race through opening prompts 	       ;
;also pushes key strokes to set startup options 			       ;
;------------------------------------------------------------------------------;

	.186

_text   segment word public 'code'
assume	cs:_text,ds:_text,es:nothing,ss:nothing


wait_out_dos	equ	0
wait_no_keys	equ	1
tick_speed	equ	2
wait_ticks	equ	3
push_timer	equ	4
pop_timer	equ	5
wait_one	equ	6
end_of_script	equ	-1

space		equ	3920h,wait_one
escp		equ	011bh,wait_one
ent		equ	1c0dh,wait_one
f2		equ	3c00h,wait_one
alt_z		equ	2c00h,wait_one
up		equ	4800h,wait_one
down		equ	5000h,wait_one
right		equ	4d00h,wait_one
left		equ	4b00h,wait_one
a		equ	1e41h,wait_one
b		equ	3042h,wait_one
c		equ	2e43h,wait_one
d		equ	2044h,wait_one
e		equ	1245h,wait_one
f		equ	2146h,wait_one
g		equ	2247h,wait_one
h		equ	2348h,wait_one
i		equ	1749h,wait_one
j		equ	244ah,wait_one
k		equ	254bh,wait_one
l		equ	264ch,wait_one
m		equ	324dh,wait_one
n		equ	314eh,wait_one
o		equ	184fh,wait_one
p		equ	1950h,wait_one
q		equ	1051h,wait_one
r		equ	1352h,wait_one
s		equ	1f53h,wait_one
t		equ	1454h,wait_one
u		equ	1655h,wait_one
v		equ	2f56h,wait_one
w		equ	1157h,wait_one
x		equ	2d58h,wait_one
y		equ	1559h,wait_one
z		equ	2c5ah,wait_one


script		label	word
		dw	push_timer,tick_speed,2048
		dw	wait_ticks,420,space
		dw	wait_ticks,280,space
		dw	wait_ticks,280,f2
		dw	tick_speed,0,pop_timer
		dw	wait_out_dos,wait_one
		dw	wait_out_dos,wait_one
		dw	wait_out_dos,wait_one
	       ; dw	 escp,w,t
		dw	escp,o,i,c,w
		dw	t,left,ent
		dw	c,up,up,up,up,up,up,up,up,left,ent
		dw	h,up,left,left,left,left,ent
		dw	u,up,up,up,up,up,up,up,left,ent
		dw	r,right,right,right,ent
		dw	w,left,up,ent
		dw	b,up,up,left,ent
		dw	e,left,ent
		dw	escp,escp,escp
		dw	end_of_script

cmd_name	db	"c:\me\me.exe",0
cmd_tail	db	40,"                                        ",13

script_ptr	dw	offset script
wait_count	dw	0
speed		dw	1
in_dos_flag	dd	0
timer		dd	0

psp_seg 	dw	0
old_vector	dd	handler

the_stack	db	2048 dup(0)


;------------------------------------------------------------------------------;
main	proc	far
;------------------------------------------------------------------------------;
	mov	ax,cs
	mov	ss,ax
	mov	sp,offset the_stack+2048
	
	mov	bx,offset end_of_program+271
	shr	bx,1
	shr	bx,1
	shr	bx,1
	shr	bx,1
	mov	ah,4ah
	int	21h

	mov	ax,cs
	mov	ds,ax
	mov	[psp_seg],es

	mov	ah,34h
	int	21h
	mov	[word ptr in_dos_flag],bx
	mov	[word ptr in_dos_flag+2],es

	mov	ax,8
	mov	bx,offset old_vector
	call	swap_int_vector

	mov	bx,offset cmd_tail
	mov	dx,offset cmd_name
	call	exec

	mov	ax,8
	mov	bx,offset old_vector
	call	swap_int_vector

	mov	ax,4c00h
	int	21h
;------------------------------------------------------------------------------;
main	endp
;------------------------------------------------------------------------------;









;------------------------------------------------------------------------------;
handler proc	far
;------------------------------------------------------------------------------;
	pusha
	push	ds
	push	es
	mov	ax,cs
	mov	ds,ax

	pushf
	call	[old_vector]

	cmp	[wait_count],0
	je	h_loop
	dec	[wait_count]
	jmp	h_done
h_loop:
	mov	bx,[script_ptr]
	mov	ax,[bx]
	cmp	ax,end_of_script
	jne	h_cont
	jmp	h_done
h_cont:
	cmp	ax,wait_out_dos
	jne	h_skip1
	les	bx,[in_dos_flag]
	mov	al,[es:bx]
	or	al,al
	je	h_ext1
	jmp	h_done
h_ext1:
	jmp	h_next
h_skip1:
	cmp	ax,wait_no_keys
	jne	h_skip2
	mov	ah,1
	int	16h
	jz	h_ext2
	jmp	h_done
h_ext2:
	jmp	h_next
h_skip2:
	cmp	ax,tick_speed
	jne	h_skip3
	mov	bx,[script_ptr]
	add	bx,2
	mov	[script_ptr],bx
	mov	bx,[bx]
        mov     al,36h                          ;set new tick speed
        out     43h,al                          ;
	mov	al,bl				;
        out     40h,al                          ;
	mov	al,bh				;
        out     40h,al                          ;
	jmp	h_next
h_skip3:
	cmp	ax,wait_ticks
	jne	h_skip4
	mov	bx,[script_ptr]
	add	bx,2
	mov	[script_ptr],bx
	mov	ax,[bx]
	mov	[wait_count],ax
	jmp	h_done
h_skip4:
	cmp	ax,wait_one
	jne	h_skip5
	add	[script_ptr],2
	jmp	h_done
h_skip5:
	cmp	ax,push_timer
	jne	h_skip6
	mov	ax,40h
	mov	es,ax
	mov	ax,[es:6ch]
	mov	[word ptr timer],ax
	mov	ax,[es:6eh]
	mov	[word ptr timer+2],ax
	jmp	h_next
h_skip6:
	cmp	ax,pop_timer
	jne	h_skip7
	mov	ax,40h
	mov	es,ax
	mov	ax,[word ptr timer]
	mov	[es:6ch],ax
	mov	ax,[word ptr timer+2]
	mov	[es:6eh],ax
	jmp	h_next
h_skip7:
	call	push_key
	jc	h_done
h_next:
	add	[script_ptr],2
	jmp	h_loop
h_done:
	pop	es
	pop	ds
	popa
	iret
;------------------------------------------------------------------------------;
handler endp
;------------------------------------------------------------------------------;









;------------------------------------------------------------------------------;
push_key	proc	near
;------------------------------------------------------------------------------;
;	pushes key into keyboard buffer 				       ;
;									       ;
;	called with:							       ;
;	  ax = ascii/scan code						       ;
;	returns:							       ;
;	  carry set = no room in buffer 				       ;
;	  carry clear = ok						       ;
;------------------------------------------------------------------------------;
key_buf_head	equ	word ptr ds:1ah     ;bios data variables
key_buf_tail	equ	word ptr ds:1ch
key_buf_start	equ	word ptr ds:80h
key_buf_end	equ	word ptr ds:82h

	push	bp
	mov	bp,sp
	pushf
	push	bx
	push	cx
	push	ds
	mov	bx,0040h		;point ds to bios data area
	mov	ds,bx
	cli

	or	byte ptr [ss:bp-2],1	;set carry in flags on stack
	mov	cx,[key_buf_tail]	;put pointer to tail of key buffer in cx
	mov	bx,cx			;copy tail to bx
	add	cx,2			;point cx to next position in buffer
	cmp	cx,[key_buf_end]	;is cx past buffer
	jne	pk_skip1		;if not then skip wrap
	mov	cx,[key_buf_start]	;wrap cx around to start of buffer
pk_skip1:
	cmp	cx,[key_buf_head]	;is cx pointing to buffer head
	je	pk_done 		;if so buffer is full so skip push
	mov	[bx],ax 		;put scan/ascii in buffer
	mov	[key_buf_tail],cx	;update buffer tail
	and	byte ptr [ss:bp-2],0feh ;clear carry in flags on stack
pk_done:
	pop	ds
	pop	cx
	pop	bx
	popf
	mov	sp,bp
	pop	bp
	ret
;-----------------------------------------------------------------------------;
push_key	endp
;-----------------------------------------------------------------------------;





;-----------------------------------------------------------------------------;
save_ss 	dw	0
save_sp 	dw	0

envseg		dw	0
cmdOff		dw	0
cmdSeg		dw	0
fcb1Off 	dw	0
fcb1Seg 	dw	0
fcb2Off 	dw	0
fcb2Seg 	dw	0
;-----------------------------------------------------------------------------;
	exec	proc	near
;-----------------------------------------------------------------------------;
;	spawns dos program						      ;
;									      ;
;	call with:							      ;
;	  [ds:dx] = program path and file name				      ;
;	  [ds:bx] = command line tail					      ;
;	returns:							      ;
;	  carry clear = program ran ok					      ;
;	    al = return code						      ;
;	  carry set = problem running program				      ;
;-----------------------------------------------------------------------------;
	pusha
	push	ds			;preserve ds so it won't get bombed!
	push	es
	mov	[cs:save_ss],ss
	mov	[cs:save_sp],sp

	push	dx			;preserve the program name!
	
;all segment registers are saved -- now, setup param block
	push	cs
	pop	es			;set it up to point to param block

;setup the command line
	mov	di,offset cs:cmdOff
	mov	ax,bx			;move the command line
	stosw
	mov	ax,ds
	stosw				;segment

;setup FCB 1
	mov	ax,05ch
	stosw
	mov	bx,[psp_seg]		;save it temporarily
	mov	ax,bx
	stosw				;segment

;setup FCB 2
	mov	ax,06ch
	stosw
	mov	ax,bx
	stosw				;segment
	
;now, the complete parameter block is setup, but we still need to create the
;	command and the default FCBs

	push	ds			;preserve
	mov	ds,[cs:cmdSeg]
	mov	si,[cs:cmdOff]
	inc	si			;point to byte after count!
	mov	es,[cs:fcb1Seg]
	mov	di,[cs:fcb1Off]
	mov	ax,02900h
	push	ax
	push	es
	int	021h
	pop	es
	pop	ax			;get command back
	mov	di,[cs:fcb2Off]
	int	021h
	pop	ds
	
;ready to do the exec!!
	pop	dx			;DS:DX => program to run
	push	cs
	pop	es
	mov	bx,offset cs:envSeg	;ES:BX => parameter block
	mov	ax,04b00h
	int	021h			;do the execute command!
	
;end of exec command -- make sure stack is restored, then restore ds and es	
	mov	ss,[cs:save_ss]
	mov	sp,[cs:save_sp]
	pop	es
	pop	ds
	popa
	mov	ax,-1
	jc	exec_end
	mov	ah,4dh
	int	21h
exec_end:
	ret
;-----------------------------------------------------------------------------;
exec	endp
;-----------------------------------------------------------------------------;







;------------------------------------------------------------------------
swap_int_vector proc	near
                ;call with:
                ;  ax=interrput number
		;  [ds:bx]=pointer to vector to swap with
;------------------------------------------------------------------------
                push    ax
                push    cx
                push    si
		push	es

                shl     ax,1
                shl     ax,1
                mov     si,ax

                sub     cx,cx
		mov	es,cx

		mov	ax,[es:si]
		mov	cx,[es:si+2]
		xchg	ax,[ds:bx]
		xchg	cx,[ds:bx+2]
                cli
		mov	[es:si],ax
		mov	[es:si+2],cx
                sti

		pop	es
                pop     si
                pop     cx
                pop     ax
                ret
;------------------------------------------------------------------------
swap_int_vector endp
;------------------------------------------------------------------------







end_of_program:



_text	ends



end	main





