;-----------------------------------------------------------------------------;
;	keyboard enhancer device driver 				      ;
;-----------------------------------------------------------------------------;

	.186

_text	segment word public 'code'
_text	ends
assume	cs:_text,ds:_text,es:nothing,ss:nothing


;-----------------------------------------------------------------------------;

buff_size	equ	128	; extended keyboard buffer size

bios_seg	equ	40h	; bios data segment
buff_head	equ	1ah	; offsets for keyboard ptrs in bios seg
buff_tail	equ	1ch
buff_start	equ	80h
buff_end	equ	82h

;-----------------------------------------------------------------------------;

req_header	struc		; device driver function request header
	rq_len		db ?		; length of request header
			db ?		; used for block device only
	rq_func 	db ?		; requested function command code
	rq_stat 	dw ?		; device driver status word
			db 8 dup (?)
	rq_data		db 1 dup (?)	; command dependent data
	rq_ptr_offset	dw ?		; returned ptr - offset
	rq_ptr_seg	dw ?		;    - segment
req_header	ends

;-----------------------------------------------------------------------------;

_text	segment

;-----------------------------------------------------------------------------;

	org	0

;	device header info

lnk_ptr 	dd	-1			; link to next device header
attrib		dw	8000h			; device attribute, char only
str_ptr 	dw	offset strategy 	; ptr to strategy routine
int_ptr 	dw	offset interrupt	; ptr to interrupt routine
dev_name	db	8 dup (0)		; device driver name

key_buff	dw	buff_size dup (?)	; the keyboard buffer

req_ptr 	dd	?			; storage for request header ptr

old_16h_vector	dd	0




;-----------------------------------------------------------------------------;
	intercept_16h	proc	far
;-----------------------------------------------------------------------------;
;-----------------------------------------------------------------------------;
	cmp	ah,3			;swallow int 16h function 3 (set typematic)
	je	skip
	jmp	[cs:old_16h_vector]
skip:
	iret
;-----------------------------------------------------------------------------;
intercept_16h	endp
;-----------------------------------------------------------------------------;


end_of_resident label	byte


install_msg	db	13,10,"George Tzeng's keyboard buffer extender installed.",13,10,"$"
		
error_msg	db	13,10,"Unable to install keyboard buffer extender.",13,10
		db	"Keyboard buffer extender must be loaded in low memory.",13,10,"$"





;-----------------------------------------------------------------------------;
	strategy	proc	far
;-----------------------------------------------------------------------------;
;-----------------------------------------------------------------------------;
	mov	word ptr cs:req_ptr,bx	; save request header ptr for later
	mov	word ptr cs:req_ptr[2],es
	ret
;-----------------------------------------------------------------------------;
strategy	endp
;-----------------------------------------------------------------------------;






;-----------------------------------------------------------------------------;
	interrupt	proc	far	; interrupt routine
;-----------------------------------------------------------------------------;
;-----------------------------------------------------------------------------;
	push	ax			; init function only assumed
	push	bx
	push	dx
	push	ds
	push	es

	mov	bx,bios_seg		; bios data segment
	mov	ax,cs			; our segment
	sub	ax,bx			; paragraph offset from bios seg
	rol	ax,4			; make it byte offset
	test	ax,0fh			; if any bits have rolled around then buffer is
	jnz	out_of_range		;   out of range
	add	ax,offset key_buff	; key board buff offset in bios seg
	jc	out_of_range		; if offset rolls then buffer is out of range

	push	ax			; save buffer offset
	mov	bx,ax			; point ds:bx to start of new key buffer
	mov	ds,bx			; bios segment
get_loop:
	mov	ah,1			; check if key in old buffer
	int	16h			;
	jz	get_out 		; if no keys then all finished
	sub	ah,ah			; get key from old buffer
	int	16h			;
	mov	[ds:bx],ax		; put key in new buffer
	add	bx,2			; index next position in new buffer
	jmp	get_loop
get_out:
	pop	ax			; restore buffer offset
	pushf
	cli				; no interruption while we do this
	mov	[ds:buff_head],ax	;
	mov	[ds:buff_tail],bx	; show keys moved into new buffer
	mov	[ds:buff_start],ax	;
	add	ax,2*buff_size		; add total length of buffer
	mov	[ds:buff_end],ax	;
	popf

	lds	bx,[cs:req_ptr] 	; request header ptr
	mov	[bx.rq_stat],0100h	; return status ok
	mov	[bx.rq_ptr_offset],offset end_of_resident
	mov	[bx.rq_ptr_seg],cs	; end of resident portion

	mov	ax,0305h		; accelerate key repeat to maximum
	sub	bx,bx			;
	int	16h			;

	sub	ax,ax			; intercept 16h functions
	mov	ds,ax			;
	mov	ax,offset intercept_16h ;
	mov	bx,cs			;
	pushf				;
	cli				;
	xchg	[ds:16h*4],ax		;
	xchg	[ds:16h*4+2],bx 	;
	mov	dx,cs			;
	mov	ds,dx			; our own ds
	mov	[word ptr old_16h_vector],ax
	mov	[word ptr old_16h_vector+2],bx
	popf				;

	mov	dx,offset install_msg	; installation message
	mov	ah,9			; display on screen
	int	21h
	jmp	short done
out_of_range:
	lds	bx,[cs:req_ptr]
	mov	[bx.rq_stat],810ch	; return error
	mov	[bx.rq_ptr_offset],0	; show no memory needed
	mov	[bx.rq_ptr_seg],cs	;

	mov	ax,cs
	mov	ds,ax			; our own ds
	mov	dx,offset error_msg	; error message
	mov	ah,9			; display on screen
	int	21h
done:
	pop	es
	pop	ds
	pop	dx
	pop	bx
	pop	ax
	ret
;-----------------------------------------------------------------------------;
interrupt	endp
;-----------------------------------------------------------------------------;



_text	ends



end
