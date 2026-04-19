;command line parser
;1-14-91  Joe Lowe
	ideal
	dosseg
	model small
	public cmd_arg
	codeseg


proc	cmd_arg

	;parses next argument from command tail
	;  places zero byte after argument in destination

	;call with:
	;  [ds:di] = destination to put string
	;  es = psp seg
	;  cx = maximum length of argument

	push	ax
	push	bx
	push	cx
	push	di
	mov	ax,ds
	mov	bx,es
	mov	es,ax
	mov	ds,bx
loop1:
	call	getcc			   ;wait for non space char
	jc	done
	cmp	al,' '
	je	loop1
loop2:
	stosb				;copy char into dest string
	dec	cx
	jcxz	done
loop3:
	call	getcc			   ;get char
	jc	done			     ;if carry then end of tail
	cmp	al,' '                      ;is it space
	je	done			     ;if not then add to dest string
	stosb
	loop	loop3
done:
	sub	al,al
	stosb				;null terminate string

	mov	ax,ds
	mov	bx,es
	mov	es,ax
	mov	ds,bx
	pop	di
	pop	cx
	pop	bx
	pop	ax
	ret

endp


proc	getcc

	;call with:
	;  ds = psp seg
	;returns:
	;  carry clear
	;    al = next character from command tail
	;  carry set
	;    end of tail
	;destroys:
	;  bx

tail_len	equ	(byte 80h)
tail_ptr	equ	(byte 81h)

	cmp	[tail_len],0
	je	no_chars
	jg	init_gcc

	sub	bh,bh
	mov	bl,[tail_ptr]
	mov	al,[bx]
	inc	[tail_len]
	inc	[tail_ptr]
	clc
	ret

init_gcc:
	mov	al,[tail_len]
	neg	al
	inc	al
	mov	[tail_len],al
	mov	al,[tail_ptr]
	mov	[tail_ptr],82h
	clc
	ret

no_chars:
	stc
	ret

endp


end
