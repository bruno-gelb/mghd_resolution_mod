# The loading screen's wait (src/mghd_resolution_mod/loading_wait.py): called instead of the game's loader by the
# single-player starts, it calls the loader, then waits for a key or a click. Returns the loader's result.
#
# loading_wait.WAIT_CODE is this, assembled with placeholder addresses that the installer replaces with each exe's:
#
#   as --32 -o wait.o loading_wait.s
#   ld -m elf_i386 -Ttext=0x10000000 --defsym LOADER=0x10000000 --defsym CAMEFROM=0x44444444 \
#      --defsym PEEK=0x11111111 --defsym DISPATCH=0x22222222 --defsym SLEEP=0x33333333 -e _start -o wait.elf wait.o
#   objcopy -O binary -j .text wait.elf wait.bin
#
# LOADER is the routine's own address, so its first call's offset comes out as -5 (e8 fbffffff); CAMEFROM is the
# global with the screen the player came from; PEEK, DISPATCH and SLEEP are the import table slots of PeekMessageA,
# DispatchMessageA and Sleep. Everything else is relative, so the routine works wherever it's put.
.intel_syntax noprefix
.code32
.globl _start
_start:
    call LOADER
    cmp dword ptr [CAMEFROM], 0x33375041   # 'AP73': started from the multiplayer staging room, no wait
    je out
    push eax                                # the loader's result
    push ebx
    push edi
    sub esp, 28                             # MSG
    mov ebx, esp

flush_keys:                                 # input pressed while loading doesn't count
    push 1                                  # PM_REMOVE
    push 0x109                              # WM_KEYLAST
    push 0x100                              # WM_KEYFIRST
    push 0
    push ebx
    call dword ptr [PEEK]
    test eax, eax
    jnz flush_keys
flush_mouse:
    push 1
    push 0x20d                              # WM_MOUSELAST
    push 0x201                              # WM_LBUTTONDOWN
    push 0
    push ebx
    call dword ptr [PEEK]
    test eax, eax
    jnz flush_mouse

    xor edi, edi                            # 0: waiting for a press; else the release message to wait for
next:
    push 0                                  # PM_NOREMOVE: look first, so a WM_QUIT stays for the game
    push 0
    push 0
    push 0
    push ebx
    call dword ptr [PEEK]
    test eax, eax
    jz idle
    cmp dword ptr [ebx + 4], 0x12           # WM_QUIT: the window was closed, stop waiting
    je done
    push 1                                  # PM_REMOVE: take it
    push 0
    push 0
    push 0
    push ebx
    call dword ptr [PEEK]
    test eax, eax
    jz next
    mov eax, dword ptr [ebx + 4]
    test edi, edi
    jnz releasing
    cmp eax, 0x100                          # WM_KEYDOWN
    je pressed
    cmp eax, 0x201                          # WM_LBUTTONDOWN
    je pressed
    cmp eax, 0x204                          # WM_RBUTTONDOWN
    je pressed
    cmp eax, 0x207                          # WM_MBUTTONDOWN
    je pressed
    jmp other
pressed:
    lea edi, [eax + 1]                      # its release: WM_KEYUP, WM_LBUTTONUP, WM_RBUTTONUP, WM_MBUTTONUP
    jmp next
releasing:
    cmp eax, edi
    je done                                 # released: the game starts without seeing the press
other:
    lea ecx, [eax - 0x100]
    cmp ecx, 9
    jbe next                                # other keyboard input: dropped
    lea ecx, [eax - 0x200]
    cmp ecx, 0xd
    jbe next                                # other mouse input: dropped
    push ebx
    call dword ptr [DISPATCH]               # anything else (painting, focus, system): to the game's window
    jmp next
idle:
    push 10
    call dword ptr [SLEEP]
    jmp next
done:
    add esp, 28
    pop edi
    pop ebx
    pop eax
out:
    ret
