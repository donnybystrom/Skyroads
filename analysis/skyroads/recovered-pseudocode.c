/* Ghidra analysis export. NOT original or buildable source.
 * x86 16-bit real mode: stack/register/segment recovery is incomplete.
 * See README.md and function-annotations.json for confidence and evidence.
 */

/* 1000:61f3 InitializeDosRuntime
Recovered MZ external entry: relative CS:IP=0000:61f3, analysis load segment=1000. Initializes DS to 1676, establishes stack, resizes DOS allocation, parses environment/command line, clears BSS, then calls RunGameSessionLoop. The original DIET stub was independently emulated to this instruction; all 30076 initialized module bytes matched. Decompiler stack recovery remains incomplete; this is not recovered source. */

// WARNING: Stack frame is not setup normally: Input value of stackpointer is not used
// WARNING: This function may have set the stack pointer
// Recovered MZ external entry: relative CS:IP=0000:61f3, analysis load segment=1000. Initializes DS
// to 1676, establishes stack, resizes DOS allocation, parses environment/command line, clears BSS,
// then calls RunGameSessionLoop. The original DIET stub was independently emulated to this
// instruction; all 30076 initialized module bytes matched. Decompiler stack recovery remains
// incomplete; this is not recovered source.

void __cdecl16far InitializeDosRuntime(void)

{
  char cVar1;
  char *pcVar2;
  char *pcVar3;
  undefined1 *puVar4;
  code *pcVar5;
  undefined2 uVar6;
  int iVar7;
  uint uVar8;
  int iVar9;
  undefined1 *puVar10;
  undefined1 *puVar11;
  char *pcVar12;
  char *pcVar13;
  char *pcVar14;
  int iVar15;
  char *pcVar16;
  char *pcVar17;
  undefined1 *puVar18;
  undefined2 unaff_ES;
  undefined2 uVar19;
  
  puVar10 = (undefined1 *)0x800;
  pcVar5 = (code *)swi(0x21);
  DAT_1676_0cc0 = unaff_ES;
  uVar6 = (*pcVar5)();
  DAT_1676_0cbe = CONCAT11((byte)uVar6,(char)((uint)uVar6 >> 8));
  if (2 < (byte)uVar6) {
    if (DAT_1676_0cbe >> 1 != 0) {
      puVar11 = puVar10 + -0x4ec0;
      pcVar5 = (code *)swi(0x21);
      (*pcVar5)();
      uVar6 = *(undefined2 *)0x2c;
      pcVar14 = (char *)0x0;
      iVar7 = -0x8000;
code_r0x0001624e:
      do {
        pcVar16 = pcVar14;
        if (iVar7 != 0) {
          iVar7 = iVar7 + -1;
          pcVar2 = pcVar14;
          pcVar14 = pcVar14 + 1;
          pcVar16 = pcVar14;
          if (*pcVar2 != '\0') goto code_r0x0001624e;
        }
        pcVar14 = pcVar16 + 1;
      } while (*pcVar16 != '\0');
      pcVar16 = pcVar16 + 3;
      iVar7 = 0x100;
      pcVar14 = pcVar16;
      do {
        if (iVar7 == 0) break;
        iVar7 = iVar7 + -1;
        pcVar2 = pcVar14;
        pcVar14 = pcVar14 + 1;
      } while (*pcVar2 != '\0');
      iVar15 = (int)pcVar14 - (int)pcVar16;
      iVar7 = -iVar15;
      pcVar14 = puVar11 + iVar7;
      *(undefined2 *)(puVar11 + iVar7 + -2) = 0x1676;
      uVar19 = *(undefined2 *)(puVar11 + iVar7 + -2);
      for (; iVar15 != 0; iVar15 = iVar15 + -1) {
        pcVar3 = pcVar14;
        pcVar14 = pcVar14 + 1;
        pcVar2 = pcVar16;
        pcVar16 = pcVar16 + 1;
        *pcVar3 = *pcVar2;
      }
      *(undefined2 *)(puVar11 + iVar7 + -2) = 0x1676;
      uVar6 = *(undefined2 *)0xcc0;
      pcVar14 = (char *)0x81;
      uVar8 = (uint)*(byte *)0x80;
      pcVar16 = (char *)((uint)(puVar11 + (iVar7 - uVar8) + -1) & 0xfffe);
      iVar15 = 0;
      pcVar17 = pcVar16;
      if (uVar8 != 0) {
        for (; uVar8 != 0; uVar8 = uVar8 - 1) {
          pcVar2 = pcVar14;
          pcVar14 = pcVar14 + 1;
          *pcVar17 = *pcVar2;
          pcVar17 = pcVar17 + 1;
        }
        *pcVar17 = '\0';
        *(undefined2 *)(pcVar16 + -2) = 0x1676;
        uVar6 = *(undefined2 *)(pcVar16 + -2);
        iVar15 = 0;
        pcVar14 = pcVar16;
        while( true ) {
          do {
            do {
              pcVar2 = pcVar14;
              pcVar14 = pcVar14 + 1;
              cVar1 = *pcVar2;
            } while (cVar1 == ' ');
          } while (cVar1 == '\t');
          if ((cVar1 == '\r') || (cVar1 == '\0')) break;
          iVar15 = iVar15 + 1;
          do {
            pcVar17 = pcVar14;
            pcVar14 = pcVar17 + 1;
            cVar1 = *pcVar17;
            if ((cVar1 == '\r') || (cVar1 == '\0')) goto LAB_1000_62c6;
          } while ((cVar1 != ' ') && (cVar1 != '\t'));
          *pcVar17 = '\0';
        }
LAB_1000_62c6:
        pcVar14 = pcVar14 + -1;
        *pcVar14 = '\0';
        for (iVar9 = iVar15; iVar9 != 0; iVar9 = iVar9 + -1) {
          do {
            do {
              pcVar2 = pcVar14;
              pcVar14 = pcVar14 + -1;
              cVar1 = *pcVar2;
            } while (cVar1 == ' ');
          } while ((cVar1 == '\t') || (cVar1 == '\0'));
          while( true ) {
            pcVar2 = pcVar14;
            pcVar17 = pcVar14 + 1;
            pcVar14 = pcVar14 + -1;
            cVar1 = *pcVar2;
            if (cVar1 == ' ') break;
            if ((cVar1 == '\t') || (cVar1 == '\0')) break;
          }
          pcVar12 = pcVar16 + -2;
          pcVar16 = pcVar16 + -2;
          *(char **)pcVar12 = pcVar17;
        }
      }
      *(int *)(pcVar16 + -2) = (int)puVar11 + iVar7;
      *(char **)(pcVar16 + -4) = pcVar16 + -2;
      pcVar13 = pcVar16 + -6;
      *(int *)(pcVar16 + -6) = iVar15 + 1;
      *(undefined2 *)(pcVar16 + -8) = 0x1676;
      uVar6 = *(undefined2 *)(pcVar16 + -8);
      puVar18 = (undefined1 *)0xe1c;
      for (iVar7 = -0x5cdc; iVar7 != 0; iVar7 = iVar7 + -1) {
        puVar4 = puVar18;
        puVar18 = puVar18 + 1;
        *puVar4 = 0;
      }
      *(undefined2 *)(pcVar16 + -8) = 0x630b;
      RunGameSessionLoop();
      pcVar5 = (code *)swi(0x21);
      (*pcVar5)();
      *(undefined2 *)(pcVar13 + -2) = *(undefined2 *)(pcVar13 + 4);
      *(undefined2 *)(pcVar13 + -4) = *(undefined2 *)(pcVar13 + 2);
      *(undefined2 *)(pcVar13 + -6) = 7;
      *(undefined2 *)(pcVar13 + -8) = 0x631d;
      uVar6 = FUN_1000_5f0c();
      *(undefined2 *)(pcVar13 + -8) = uVar6;
      *(undefined2 *)(pcVar13 + -10) = 0x6321;
      PrintConsoleString();
      return;
    }
    pcVar5 = (code *)swi(0x21);
    (*pcVar5)();
  }
  *(undefined2 *)(puVar10 + -2) = unaff_ES;
  *(undefined2 *)(puVar10 + -4) = 0;
  return;
}



/* 1000:01b8 RunGameSessionLoop
High-confidence orchestration function: VGA/EGA detection, timer/resource initialization, menu/selection flow, road loading, repeated RunRoadSession calls and completion bookkeeping. Mode values and all global types remain provisional. */

// High-confidence orchestration function: VGA/EGA detection, timer/resource initialization,
// menu/selection flow, road loading, repeated RunRoadSession calls and completion bookkeeping. Mode
// values and all global types remain provisional.

void __cdecl16near RunGameSessionLoop(void)

{
  int *piVar1;
  bool bVar2;
  int iVar3;
  uint uVar4;
  undefined2 uVar5;
  int iVar6;
  undefined2 unaff_DS;
  uint local_8;
  
  local_8 = 0xffff;
  iVar3 = ProbeVgaSupport();
  if (iVar3 == 0) {
    *(undefined2 *)0x3c = 0;
    iVar3 = ProbeEgaSupport();
    if (iVar3 == 0) {
      PrintConsoleString(0xd08);
      return;
    }
  }
  FUN_1000_5a98();
  FUN_1000_58cd();
  InstallTimerHandlers();
  *(undefined2 *)0x4570 = 1;
  FUN_1000_0000();
  FUN_1000_5737();
  FUN_1000_57c4(0);
  FUN_1000_5508();
  LoadTrekDataArchive();
  AbortOnResourceError();
  FUN_1000_2cce();
LAB_1000_0219:
  bVar2 = true;
  iVar3 = FUN_1000_4591();
  if (iVar3 == 0) {
    *(undefined2 *)0x95f6 = 3;
    goto LAB_1000_0251;
  }
LAB_1000_0232:
  *(undefined2 *)0x95f6 = *(undefined2 *)0x4518;
  FUN_1000_4e52(!bVar2);
LAB_1000_0251:
  bVar2 = false;
  FUN_1000_3f20();
  FUN_1000_5567();
  do {
    FUN_1000_3f20();
    if (*(int *)0x95f6 == 3) {
      uVar5 = LoadRoadByIndex(0);
      *(undefined2 *)0x41c0 = uVar5;
      FUN_1000_5387(0);
    }
    else {
      iVar3 = FUN_1000_5180();
      if (iVar3 != 0) {
        FUN_1000_3f3b();
        FUN_1000_3f3b();
        goto LAB_1000_0232;
      }
      *(undefined2 *)0x95f6 = *(undefined2 *)0x4518;
      uVar4 = FUN_1000_019c();
      uVar4 = uVar4 % 9;
      if (uVar4 == local_8) {
        uVar4 = (uVar4 + 1) % 9;
      }
      FUN_1000_57c4(uVar4 + 1);
      uVar5 = LoadRoadByIndex(*(int *)0x9332 + 1);
      *(undefined2 *)0x41c0 = uVar5;
      FUN_1000_5387(*(uint *)0x9332 / 3);
      local_8 = uVar4;
    }
    if (*(int *)0x3c != 0) {
      uVar5 = FUN_1000_3ef4(0xac80,0);
      *(undefined2 *)0x5478 = uVar5;
    }
    AbortOnResourceError();
    FUN_1000_0707();
    iVar3 = 0;
    for (uVar4 = 0; uVar4 < 0x1e; uVar4 = uVar4 + 1) {
      if (*(int *)(uVar4 * 2 + 0x451c) != 0) {
        iVar3 = iVar3 + 1;
      }
    }
    do {
      FUN_1000_4153();
      if ((*(int *)(*(int *)0x9332 * 2 + 0x451c) == 0) && (iVar3 == 0x1d)) {
        uVar5 = 1;
      }
      else {
        uVar5 = 0;
      }
      iVar6 = RunRoadSession(uVar5);
      if (*(int *)0x95f6 == 3) {
        FUN_1000_3f3b();
        FUN_1000_3f3b();
        if (iVar6 != 7) goto LAB_1000_0219;
        goto LAB_1000_0232;
      }
      if (iVar6 == 0) {
        piVar1 = (int *)(*(int *)0x9332 * 2 + 0x451c);
        *piVar1 = *piVar1 + 1;
        *(int *)0x9332 = *(int *)0x9332 + 1;
        FUN_1000_578c();
      }
    } while ((iVar6 != 7) && (iVar6 != 0));
    FUN_1000_3f3b();
  } while( true );
}



/* 1000:0069 AbortOnResourceError
Checks DS:41aa error state. Restores text mode/handlers and prints 'Not enough memory' for code 8, otherwise 'Error loading data files'; then terminates. DS:41aa semantics inferred from DOS wrapper writes. */

// Checks DS:41aa error state. Restores text mode/handlers and prints 'Not enough memory' for code
// 8, otherwise 'Error loading data files'; then terminates. DS:41aa semantics inferred from DOS
// wrapper writes.

void __cdecl16near AbortOnResourceError(void)

{
  undefined2 unaff_DS;
  
  if (*(int *)0x41aa != 0) {
    FUN_1000_601d(3);
    FUN_1000_3b6b();
    FUN_1000_58a5();
    if (*(int *)0x41aa == 8) {
      PrintConsoleString(0xcc2);
    }
    else {
      PrintConsoleString(0xcd4);
      FUN_1000_630f(*(undefined2 *)0x41aa,0);
    }
    FUN_1000_60e9();
  }
  return;
}



/* 1000:00bb LoadTrekDataArchive
Opens filename at DS:0cfc ('trekdat.lzs'). Initializes buffered input, reads two little-endian words per record, allocates record storage, writes size difference, and calls DecodeLzsBlock. Ends on shared input/error state; exact record semantics and EOF treatment are not yet reconstructed. */

// Opens filename at DS:0cfc ('trekdat.lzs'). Initializes buffered input, reads two little-endian
// words per record, allocates record storage, writes size difference, and calls DecodeLzsBlock.
// Ends on shared input/error state; exact record semantics and EOF treatment are not yet
// reconstructed.

void __cdecl16near LoadTrekDataArchive(void)

{
  undefined2 uVar1;
  int iVar2;
  int iVar3;
  undefined2 uVar4;
  uint uVar5;
  undefined2 unaff_DS;
  undefined4 local_6;
  
  uVar1 = OpenFileReadOnly(0xcfc);
  InitializeBufferedInput(uVar1,0,0x1000,0);
  *(undefined2 *)0x54a8 = 0;
  while (*(int *)0x41aa == 0) {
    iVar2 = ReadBufferedWordLE();
    iVar3 = ReadBufferedWordLE();
    if (*(int *)0x41aa == 0) {
      if (*(int *)0x4560 == 0) {
        uVar4 = FUN_1000_3ef4(0x7d64,0);
        *(undefined2 *)0x4560 = uVar4;
        if ((*(int *)0x4560 + 0x7d7U & 0xf000) != (*(uint *)0x4560 & 0xf000)) {
          FUN_1000_3f72();
          *(undefined2 *)0x4560 = 0;
        }
      }
      uVar5 = FUN_1000_3ef4(iVar2,0);
      *(uint *)(*(int *)0x54a8 * 2 + 0xe76) = uVar5;
      local_6 = (int *)((ulong)uVar5 << 0x10);
      *local_6 = iVar2 - iVar3;
      if (*(int *)0x41aa == 0) {
        DecodeLzsBlock(iVar2 - iVar3,uVar5,iVar3);
      }
    }
    *(int *)0x54a8 = *(int *)0x54a8 + 1;
  }
  FUN_1000_5c11();
  CloseFileHandle(uVar1);
  return;
}



/* 1000:5614 LoadRoadByIndex
Opens DS:0e08 ('roads.lzs'). Seeks index*4, reads uint16 file offset and uint16 decoded length, then seeks to block. Reads 3 uint16 metadata fields into DS:4562/54a2/4566; copies 216 bytes to DS:41c2, then decodes length bytes into far pointer DS:162c. Clears 7000-byte destination first; returns decoded_length/14. Metadata field meanings and tile bit layout remain unverified. */

// Opens DS:0e08 ('roads.lzs'). Seeks index*4, reads uint16 file offset and uint16 decoded length,
// then seeks to block. Reads 3 uint16 metadata fields into DS:4562/54a2/4566; copies 216 bytes to
// DS:41c2, then decodes length bytes into far pointer DS:162c. Clears 7000-byte destination first;
// returns decoded_length/14. Metadata field meanings and tile bit layout remain unverified.

uint __cdecl16near LoadRoadByIndex(int param_1)

{
  undefined2 uVar1;
  undefined2 unaff_DS;
  undefined2 local_8;
  uint local_6;
  undefined2 local_4;
  
  FUN_1000_5d07(0x162c,0,7000);
  local_4 = OpenFileReadOnly(0xe08);
  FUN_1000_5ca6(local_4,param_1 << 2,0,0);
  FUN_1000_5f7d(local_4,&local_8,2);
  FUN_1000_5f7d(local_4,&local_6,2);
  FUN_1000_5ca6(local_4,local_8,0,0);
  InitializeBufferedInput(local_4,0,0x1000,0);
  uVar1 = ReadBufferedWordLE();
  *(undefined2 *)0x4562 = uVar1;
  uVar1 = ReadBufferedWordLE();
  *(undefined2 *)0x54a2 = uVar1;
  uVar1 = ReadBufferedWordLE();
  *(undefined2 *)0x4566 = uVar1;
  FUN_1000_6595(0x41c2);
  DecodeLzsBlock(0x162c);
  CloseFileHandle(local_4);
  return local_6 / 0xe;
}



/* 1000:2b3d RunRoadSession
Sets up road presentation, calls RunGameplayLoop, and on result 0 displays 'Road completed' or 'The End', selected by caller argument. Restores session resources and returns gameplay result. */

// Sets up road presentation, calls RunGameplayLoop, and on result 0 displays 'Road completed' or
// 'The End', selected by caller argument. Restores session resources and returns gameplay result.

int __cdecl16near RunRoadSession(int param_1)

{
  int iVar1;
  int iVar2;
  int unaff_DS;
  
  *(int *)0xaf2a = unaff_DS + 0x31b;
  FUN_1000_3b9d();
  *(undefined2 *)0xaf1e = 0;
  *(undefined2 *)0x455c = 0;
  *(undefined2 *)0x960c = 0;
  *(undefined2 *)0x456c = 0;
  *(undefined2 *)0x41be = 0;
  *(undefined2 *)0xaf20 = 0xffff;
  *(undefined2 *)0x9334 = 0;
  if (*(int *)0x3c == 0) {
    FUN_1000_2b0f(0xa000,*(undefined2 *)0x5170);
    FUN_1000_2b0f(0xa200,*(undefined2 *)0x5170);
  }
  else {
    FUN_1000_6053(0xac80,0xa000,0xac80,*(undefined2 *)0x5170,0x4d80);
  }
  FUN_1000_1114(0x60,0x9c,(*(int *)0x4562 + -3) * 100,4);
  if (*(int *)0x3c == 0) {
    iVar1 = (uint)(*(int *)0x9334 == 0) * 0x200 + -0x6000;
  }
  else {
    iVar1 = *(int *)0x5478;
  }
  iVar1 = FUN_1000_0baf(0,0x2800,1,0,iVar1);
  iVar2 = FUN_1000_0be9(0x8000);
  FUN_1000_2d1f(0x100,0x18,0x50,*(int *)0xaf34 + ((iVar2 * 3 + iVar1) * 3 + 0xe) * 0x2d0,
                *(undefined2 *)0xaf36);
  FUN_1000_4b8e(0x41c2,1,0x24);
  iVar1 = RunGameplayLoop();
  if (*(int *)0x9334 != 0) {
    *(undefined2 *)0x9334 = 0;
    FUN_1000_0ed0();
  }
  if (iVar1 == 0) {
    FUN_1000_3c9a();
    if (param_1 == 0) {
      FUN_1000_4526(0x68,0x50,0xd42,99);
    }
    else {
      FUN_1000_4526(0x84,0x50,0xd3a,99);
    }
    FUN_1000_4459(0x1b);
  }
  FUN_1000_4b8e(0x41c2,0,0x24);
  FUN_1000_3c03();
  return iVar1;
}



/* 1000:1fd9 RunGameplayLoop
Provisional semantic name, supported by repeated tick-synchronized input/render/update loop, collision-style helper calls, movement arithmetic and exit reasons. Returns 7 on tested key flag; exact controls, physics units, and global meanings need tracing. Contains significant decompiler uncertainty. */

// Provisional semantic name, supported by repeated tick-synchronized input/render/update loop,
// collision-style helper calls, movement arithmetic and exit reasons. Returns 7 on tested key flag;
// exact controls, physics units, and global meanings need tracing. Contains significant decompiler
// uncertainty.

undefined2 __cdecl16near RunGameplayLoop(void)

{
  uint *puVar1;
  uint uVar2;
  bool bVar3;
  bool bVar4;
  bool bVar5;
  int iVar6;
  undefined2 uVar7;
  int iVar8;
  uint uVar9;
  undefined2 unaff_DS;
  bool bVar10;
  bool bVar11;
  bool bVar12;
  undefined4 uVar13;
  long lVar14;
  int local_24;
  uint local_22;
  int local_20;
  int local_1e;
  uint local_1c;
  uint local_1a;
  uint local_18;
  uint local_16;
  int local_c;
  uint local_4;
  
  if (*(int *)0x95f6 == 2) {
    FUN_1000_06a4(0xa0,100);
  }
  *(undefined2 *)0x516e = 0;
  uVar13 = FUN_1000_5d4c(*(undefined2 *)0x4562,0,0x1680,0);
  iVar6 = FUN_1000_5d8c(uVar13,400,0);
  *(int *)0x54aa = -iVar6;
  *(undefined2 *)0x9618 = 0;
  *(undefined2 *)0x961a = 3;
  *(undefined2 *)0xaf1c = 0x8000;
  *(undefined2 *)0xaf2c = 0x2800;
  *(undefined2 *)0x5496 = 0;
  *(undefined2 *)0x4568 = 0;
  *(undefined2 *)0x9336 = 0;
  *(undefined2 *)0x54ac = 0;
  *(undefined2 *)0x54ae = 0;
  *(undefined2 *)0x5494 = 30000;
  *(undefined2 *)0xb13c = 30000;
  *(undefined2 *)0x456e = 0;
  *(undefined2 *)0x4558 = 0;
  *(undefined2 *)0x456a = 0;
  bVar3 = true;
  bVar12 = false;
  bVar11 = false;
  *(undefined2 *)0x455a = 0;
  bVar5 = false;
  bVar4 = false;
  *(undefined2 *)0xaf2e = 0;
  *(undefined2 *)0xaf30 = 0;
  *(undefined2 *)0x1600 = 0;
  local_4 = 0;
  *(undefined2 *)0xaf38 = 0;
  do {
    if (*(uint *)0x1600 < local_4) {
      *(undefined2 *)0x1600 = 0;
      local_4 = 0;
    }
    iVar6 = *(int *)0x1600;
    if ((*(byte *)0xbdc & 0x80) != 0) {
      do {
      } while ((*(byte *)0xbdc & 0x80) != 0);
      while ((((((*(byte *)0xbd2 & 0x80) == 0 && ((*(byte *)0xbd3 & 0x80) == 0)) &&
               ((*(byte *)0xbd4 & 0x80) == 0)) &&
              (((*(byte *)0xbd5 & 0x80) == 0 && ((*(byte *)0xbd6 & 0x80) == 0)))) &&
             ((((*(byte *)0xbd7 & 0x80) == 0 &&
               (((*(byte *)0xbd8 & 0x80) == 0 && ((*(byte *)0xbd9 & 0x80) == 0)))) &&
              ((*(byte *)0xbda & 0x80) == 0))))) {
        if (((*(byte *)0xbdb & 0x80) != 0) || ((*(byte *)0xbdc & 0x80) != 0)) break;
      }
      if ((*(byte *)0xbda & 0x80) != 0) {
        return 7;
      }
      do {
        do {
        } while ((*(byte *)0xbd2 & 0x80) != 0);
      } while (((((((*(byte *)0xbd3 & 0x80) != 0) || ((*(byte *)0xbd4 & 0x80) != 0)) ||
                 ((*(byte *)0xbd5 & 0x80) != 0)) ||
                ((((*(byte *)0xbd6 & 0x80) != 0 || ((*(byte *)0xbd7 & 0x80) != 0)) ||
                 (((*(byte *)0xbd8 & 0x80) != 0 ||
                  (((*(byte *)0xbd9 & 0x80) != 0 || ((*(byte *)0xbda & 0x80) != 0)))))))) ||
               ((*(byte *)0xbdb & 0x80) != 0)) || ((*(byte *)0xbdc & 0x80) != 0));
      *(int *)0x1600 = iVar6;
    }
    if ((*(byte *)0xbda & 0x80) != 0) {
      return 7;
    }
    if (((*(int *)0x456a == 0) || (0x2a < *(uint *)0x456a)) &&
       (((*(int *)0x456e == 1 || (*(int *)0x456e == 2)) ||
        (((*(int *)0x456e == 3 && (*(int *)0x456a != 0)) || (0x6b < *(uint *)0x4558)))))) {
      return *(undefined2 *)0x456e;
    }
    FUN_1000_0c98(bVar12);
    FUN_1000_12f8();
    do {
    } while (*(int *)0x1600 == iVar6);
    FUN_1000_0ed0();
    if (*(int *)0x95f6 != 3) {
      FUN_1000_074c();
    }
    for (; local_4 < *(uint *)0x1600; local_4 = local_4 + 1) {
      if (*(int *)0x95f6 == 3) {
        FUN_1000_074c();
      }
      local_16 = FUN_1000_04c0(*(undefined2 *)0x9618,*(undefined2 *)0x961a,*(undefined2 *)0xaf1c);
      bVar10 = local_16 != 0;
      if (bVar3) {
        if (0x2800 < *(uint *)0xaf2c) {
          if (*(int *)0xaf2c == *(int *)((local_16 >> 8) * 2 + 0xe4)) {
            local_16 = local_16 >> 4;
          }
          else {
            local_16 = 0;
          }
        }
        FUN_1000_1b49(local_16);
        bVar11 = (local_16 & 0xf) == 8;
        bVar12 = (local_16 & 0xf) == 2;
      }
      else {
        bVar12 = false;
      }
      lVar14 = FUN_1000_5d80();
      uVar9 = (uint)((ulong)(lVar14 + -0x8000) >> 0x10);
      if (((uVar9 <= *(uint *)0x961a) &&
          ((uVar9 < *(uint *)0x961a || ((uint)(lVar14 + -0x8000) <= *(uint *)0x9618)))) &&
         ((iVar6 = FUN_1000_0533(*(undefined2 *)0x9618,*(undefined2 *)0x961a,*(undefined2 *)0xaf1c,
                                 *(undefined2 *)0xaf2c), iVar6 != 0 && (*(int *)0x456e == 0)))) {
        uVar7 = FUN_1000_0f05();
        return uVar7;
      }
      if (*(int *)0xaf2c != local_1e) {
        if ((*(int *)0x5496 == 0) || (1 < local_1a)) {
          if (*(int *)0x9336 < 1) {
            uVar9 = -*(int *)0x9336;
          }
          else {
            uVar9 = *(uint *)0x9336;
          }
          if (((uint)(((long)*(int *)0x4562 * 0x104 & 0xffffU) / 8) <= uVar9) &&
             (*(int *)0x456a == 0)) {
            if ((*(int *)0x456e == 0) &&
               ((*(int *)0x9336 < 0 && (iVar6 = FUN_1000_0476(), iVar6 == 0)))) {
              FUN_1000_03c2(1);
            }
            *(int *)0x9336 = (*(int *)0x9336 * -5) / 10;
            goto LAB_1000_24ba;
          }
        }
        *(undefined2 *)0x9336 = 0;
      }
LAB_1000_24ba:
      if (*(int *)0x456e == 0) {
        uVar13 = FUN_1000_5d4c(*(int *)0x9330,*(int *)0x9330 >> 0xf,0x4b,0);
        puVar1 = (uint *)0x54ac;
        uVar9 = *puVar1;
        *puVar1 = *puVar1 + (uint)uVar13;
        *(int *)0x54ae =
             *(int *)0x54ae + (int)((ulong)uVar13 >> 0x10) + (uint)CARRY2(uVar9,(uint)uVar13);
        if ((*(int *)0x54ae < 1) && (*(int *)0x54ae < 0)) {
          *(undefined2 *)0x54ac = 0;
          *(undefined2 *)0x54ae = 0;
        }
        else if ((-1 < *(int *)0x54ae) && ((0 < *(int *)0x54ae || (0x2aaa < *(uint *)0x54ac)))) {
          *(undefined2 *)0x54ac = 0x2aaa;
          *(undefined2 *)0x54ae = 0;
        }
        if ((!bVar11) &&
           (((!bVar4 && (bVar10)) ||
            ((*(int *)0x4568 == 0 &&
             ((0 < *(int *)0x9336 && ((uint)(*(int *)0xaf2c - local_c) < 0xf00)))))))) {
          *(int *)0x4568 = *(int *)0x95f4 * 0x1d;
        }
        if ((((!bVar4) && (bVar10)) && (*(int *)0x547a != 0)) && (*(uint *)0x4562 < 0x14)) {
          *(undefined2 *)0x9336 = 0x480;
          *(undefined2 *)0x5494 = *(undefined2 *)0x5494;
          bVar4 = true;
          local_c = *(int *)0xaf2c;
        }
      }
      if (((*(int *)0x4570 != 0) && (bVar4)) && ((!bVar5 && (0x36ff < *(uint *)0xaf2c)))) {
        FUN_1000_1dfa();
        bVar5 = true;
      }
      if (*(int *)0x456a == 0) {
        if (*(uint *)0xaf2c < 0x2800) {
          if (-0x6a < *(int *)0x9336) {
            *(undefined2 *)0x9336 = 0xff96;
          }
        }
        else {
          *(int *)0x9336 = *(int *)0x9336 + *(int *)0x54aa;
        }
      }
      else {
        if (*(int *)0x9336 < 0) {
          *(undefined2 *)0x9336 = 0;
        }
        if (*(int *)0x9336 < 0x47) {
          *(int *)0x9336 = *(int *)0x9336 + 0x27;
        }
        else {
          *(undefined2 *)0x9336 = 0x47;
        }
      }
      local_22 = *(uint *)0x54ac + *(uint *)0x9618;
      local_20 = *(int *)0x54ae + *(int *)0x961a + (uint)CARRY2(*(uint *)0x54ac,*(uint *)0x9618);
      iVar6 = *(int *)0x5496;
      if (bVar12 == false) {
        uVar9 = 0x618;
      }
      else {
        uVar9 = 0;
      }
      uVar13 = FUN_1000_5d4c(uVar9 + *(uint *)0x54ac,
                             *(int *)0x54ae + (uint)CARRY2(uVar9,*(uint *)0x54ac),*(int *)0x4568,
                             *(int *)0x4568 >> 0xf);
      iVar8 = FUN_1000_5e5a(uVar13,0x200,0);
      local_1c = iVar8 + *(int *)0xaf1c + iVar6;
      local_1e = *(int *)0x9336 + *(int *)0xaf2c;
      if (((*(uint *)0xaf1c < 0x2f80) && (0xd080 < local_1c)) ||
         ((local_1c < 0x2f80 && (0xd080 < *(uint *)0xaf1c)))) {
        local_1c = *(uint *)0xaf1c;
      }
      FUN_1000_186b(local_22,local_20,local_1c,local_1e);
      if ((((*(uint *)0x9618 != local_22) || (*(int *)0x961a != local_20)) &&
          (*(uint *)0xaf1c == local_1c)) &&
         (iVar6 = FUN_1000_1732(local_22,local_20,*(undefined2 *)0xaf1c,*(undefined2 *)0xaf2c),
         iVar6 != 0)) {
        iVar6 = FUN_1000_1732(local_22,local_20,*(int *)0xaf1c + -0x3a0,*(undefined2 *)0xaf2c);
        if (iVar6 == 0) {
          *(int *)0xaf1c = *(int *)0xaf1c + -0x3a0;
          local_22 = *(uint *)0x9618;
          local_20 = *(int *)0x961a;
          FUN_1000_03c2(2);
        }
        else {
          iVar6 = FUN_1000_1732(local_22,local_20,*(int *)0xaf1c + 0x3a0,*(undefined2 *)0xaf2c);
          if (iVar6 == 0) {
            *(int *)0xaf1c = *(int *)0xaf1c + 0x3a0;
            local_22 = *(uint *)0x9618;
            local_20 = *(int *)0x961a;
            FUN_1000_03c2(2);
          }
        }
      }
      if ((*(uint *)0x9618 != local_22) || (*(int *)0x961a != local_20)) {
        if (((*(int *)0x54ae < 0) || ((*(int *)0x54ae < 1 && (*(uint *)0x54ac < 0xe38)))) ||
           (*(int *)0x456a != 0)) {
          uVar9 = (local_20 - *(int *)0x54ae) - (uint)(local_22 < *(uint *)0x54ac);
          if ((uVar9 <= *(uint *)0x961a) &&
             ((uVar9 < *(uint *)0x961a || (local_22 - *(uint *)0x54ac < *(uint *)0x9618)))) {
            FUN_1000_03c2(2);
          }
        }
        else {
          *(undefined2 *)0x456a = 1;
          FUN_1000_03c2(0);
          if (*(int *)0x456e == 0) {
            *(undefined2 *)0x456e = 1;
          }
        }
        *(undefined2 *)0x54ac = 0;
        *(undefined2 *)0x54ae = 0;
      }
      if (*(uint *)0xaf1c != local_1c) {
        *(undefined2 *)0x4568 = 0;
        if (((0 < *(int *)0x5496) && (*(uint *)0xaf1c < local_1c)) ||
           ((*(int *)0x5496 < 0 && (local_1c < *(uint *)0xaf1c)))) {
          *(undefined2 *)0x5496 = 0;
        }
        puVar1 = (uint *)0x54ac;
        uVar9 = *puVar1;
        *puVar1 = *puVar1 - 0x97;
        *(int *)0x54ae = *(int *)0x54ae - (uint)(uVar9 < 0x97);
        if ((*(int *)0x54ae < 1) && (*(int *)0x54ae < 0)) {
          *(undefined2 *)0x54ac = 0;
          *(undefined2 *)0x54ae = 0;
        }
        else if ((-1 < *(int *)0x54ae) && ((0 < *(int *)0x54ae || (0x2aaa < *(uint *)0x54ac)))) {
          *(undefined2 *)0x54ac = 0x2aaa;
          *(undefined2 *)0x54ae = 0;
        }
      }
      bVar3 = false;
      if ((*(int *)0xaf2c != local_1e) && (*(int *)0x9336 < 0)) {
        *(undefined2 *)0x455a = 0;
        bVar5 = false;
        bVar4 = false;
        bVar3 = true;
        uVar2 = *(uint *)0xaf2e;
        iVar6 = *(int *)0xaf30;
        puVar1 = (uint *)0x54ac;
        uVar9 = *puVar1;
        *puVar1 = *puVar1 - uVar2;
        *(int *)0x54ae = (*(int *)0x54ae - iVar6) - (uint)(uVar9 < uVar2);
        if ((*(int *)0x54ae < 1) && (*(int *)0x54ae < 0)) {
          *(undefined2 *)0x54ac = 0;
          *(undefined2 *)0x54ae = 0;
        }
        else if ((-1 < *(int *)0x54ae) && ((0 < *(int *)0x54ae || (0x2aaa < *(uint *)0x54ac)))) {
          *(undefined2 *)0x54ac = 0x2aaa;
          *(undefined2 *)0x54ae = 0;
        }
        *(undefined2 *)0xaf2e = 0;
        *(undefined2 *)0xaf30 = 0;
        local_24 = 0;
        for (local_18 = 1; local_18 < 0xf; local_18 = local_18 + 1) {
          iVar6 = FUN_1000_1732(*(undefined2 *)0x9618,*(undefined2 *)0x961a,
                                local_18 * 0x80 + *(int *)0xaf1c,*(int *)0xaf2c + -1);
          if (iVar6 == 0) {
            local_24 = 1;
            local_1a = local_18;
            break;
          }
        }
        for (local_18 = 1; local_18 < 0xf; local_18 = local_18 + 1) {
          iVar6 = FUN_1000_1732(*(undefined2 *)0x9618,*(undefined2 *)0x961a,
                                *(int *)0xaf1c + local_18 * -0x80,*(int *)0xaf2c + -1);
          if (iVar6 == 0) {
            local_24 = local_24 + -1;
            local_1a = local_18;
            break;
          }
        }
        if (local_24 == 0) {
          *(undefined2 *)0x5496 = 0;
        }
        else {
          *(int *)0x5496 = *(int *)0x5496 + local_24 * 0x11;
        }
      }
      if (0x7fff < *(uint *)0xaf2c) {
        *(undefined2 *)0xaf2c = 0;
      }
      if (*(int *)0x456e == 0) {
        *(int *)0xb13c = *(int *)0xb13c - (int)(30000 / ((long)*(int *)0x4566 * 0x24 & 0xffffU));
        if (30000 < *(uint *)0xb13c) {
          *(undefined2 *)0xb13c = 0;
        }
        uVar13 = FUN_1000_5d4c((int)(30000 / (ulong)*(uint *)0x54a2),0,*(undefined2 *)0x54ac,
                               *(undefined2 *)0x54ae);
        iVar6 = FUN_1000_5e5a(uVar13,0,1);
        *(int *)0x5494 = *(int *)0x5494 - iVar6;
        if (30000 < *(uint *)0x5494) {
          *(undefined2 *)0x5494 = 0;
        }
      }
      if (*(int *)0x456e == 0) {
        if (*(uint *)0xaf2c < 0x2800) {
          *(undefined2 *)0x456e = 3;
        }
        if (*(int *)0x5494 == 0) {
          *(undefined2 *)0x456e = 4;
        }
        if (*(int *)0xb13c == 0) {
          *(undefined2 *)0x456e = 5;
        }
      }
      else {
        *(int *)0x4558 = *(int *)0x4558 + 1;
      }
      if (*(int *)0x456a != 0) {
        *(int *)0x456a = *(int *)0x456a + 1;
      }
    }
  } while( true );
}



/* 1000:3acc InstallTimerHandlers
Replaces real-mode interrupt vectors 08h (linear20h) and24h (linear90h), retains old08h vector, programs PIT ports43h/40h with divisor19e4h and speaker channel42h with divisor0002h. Hardware behavior not executed. */

// Replaces real-mode interrupt vectors 08h (linear20h) and24h (linear90h), retains old08h vector,
// programs PIT ports43h/40h with divisor19e4h and speaker channel42h with divisor0002h. Hardware
// behavior not executed.

uint __cdecl16near InstallTimerHandlers(void)

{
  uint uVar1;
  
  uVar1 = uRam00000020;
  DAT_1000_3b67 = uRam00000020;
  DAT_1000_3b69 = uRam00000022;
  uRam00000020 = 0x3b17;
  uRam00000022 = 0x1000;
  uRam00000090 = 0x3b14;
  uRam00000092 = 0x1000;
  out(0x43,0x36);
  out(0x40,0xe4);
  out(0x40,0x19);
  out(0x43,0xb6);
  out(0x42,2);
  out(0x42,0);
  return uVar1 & 0xff00;
}



/* 1000:5c77 OpenFileReadOnly
DOS open wrapper: loads filename argument into DX and AX=3d00h, then calls shared INT21/error wrapper. ABI/return signature not fully recovered. */

// DOS open wrapper: loads filename argument into DX and AX=3d00h, then calls shared INT21/error
// wrapper. ABI/return signature not fully recovered.

void OpenFileReadOnly(void)

{
  FUN_1000_5bf8();
  return;
}



/* 1000:5c59 CloseFileHandle
DOS INT21 AH=3eh close wrapper; skips close when DS:41aa equals15h. Handle is a near-stack argument at SP+2, loaded into BX. Current decompiler signature omits that argument. */

// DOS INT21 AH=3eh close wrapper; consults shared DS:41aa error state. Register-based handle
// parameter is not reflected reliably by the current decompiler signature.

void __cdecl16near CloseFileHandle(void)

{
  code *pcVar1;
  undefined2 unaff_DS;
  
  if (*(int *)0x41aa != 0x15) {
    pcVar1 = (code *)swi(0x21);
    (*pcVar1)();
  }
  return;
}



/* 1000:5c82 PrintConsoleString
Walks NUL-terminated string and calls WriteConsoleCharacter. Uses DS-relative near pointer. */

// Walks NUL-terminated string and calls WriteConsoleCharacter. Uses DS-relative near pointer.

void __cdecl16near PrintConsoleString(char *param_1)

{
  char *pcVar1;
  undefined2 unaff_DS;
  
  while( true ) {
    pcVar1 = param_1;
    param_1 = param_1 + 1;
    if (*pcVar1 == '\0') break;
    WriteConsoleCharacter(*pcVar1);
  }
  return;
}



/* 1000:5fd4 WriteConsoleCharacter
DOS INT21 AH=02h, DL=character. Emits carriage return before newline (LF) to produce CRLF. */

// DOS INT21 AH=02h, DL=character. Emits carriage return before newline (LF) to produce CRLF.

void __cdecl16near WriteConsoleCharacter(char param_1)

{
  code *pcVar1;
  
  if (param_1 == '\n') {
    pcVar1 = (code *)swi(0x21);
    (*pcVar1)();
  }
  pcVar1 = (code *)swi(0x21);
  (*pcVar1)();
  return;
}



/* 1000:6027 ProbeEgaSupport
BIOS INT10 AH=12h BL=10h; returns true if BL was changed and is at least3. Name describes use as fallback EGA support check; hardware behavior not exercised. */

// BIOS INT10 AH=12h BL=10h; returns true if BL was changed and is at least3. Name describes use as
// fallback EGA support check; hardware behavior not exercised.

undefined2 __cdecl16near ProbeEgaSupport(void)

{
  code *pcVar1;
  undefined2 uVar2;
  byte bVar3;
  
  bVar3 = 0x10;
  pcVar1 = (code *)swi(0x10);
  (*pcVar1)();
  uVar2 = 0;
  if ((bVar3 != 0x10) && (2 < bVar3)) {
    uVar2 = 1;
  }
  return uVar2;
}



/* 1000:603b ProbeVgaSupport
BIOS INT10 AX=1a00h; requires returned AL=1ah and BL in[7,8], the VGA display-combination codes. Hardware behavior not exercised. */

// BIOS INT10 AX=1a00h; requires returned AL=1ah and BL in[7,8], the VGA display-combination codes.
// Hardware behavior not exercised.

undefined2 __cdecl16near ProbeVgaSupport(void)

{
  code *pcVar1;
  char cVar2;
  undefined2 uVar3;
  byte in_BL;
  
  pcVar1 = (code *)swi(0x10);
  cVar2 = (*pcVar1)();
  uVar3 = 0;
  if (((cVar2 == '\x1a') && (6 < in_BL)) && (in_BL < 9)) {
    uVar3 = 1;
  }
  return uVar3;
}



/* 1000:6420 InitializeBufferedInput
Stores input handle at DS:41ac, prepares buffer via63f0, refills via6364, resets bitreader/EOF flags. Used by archive and road loading. */

// Stores input handle at DS:41ac, prepares buffer via63f0, refills via6364, resets bitreader/EOF
// flags. Used by archive and road loading.

void __cdecl16near
InitializeBufferedInput(undefined2 param_1,undefined2 param_2,undefined2 param_3,undefined1 param_4)

{
  undefined2 unaff_DS;
  
  *(undefined2 *)0x41ac = param_1;
  *(undefined1 *)0x41bc = param_4;
  *(undefined1 *)0x41bb = 0;
  FUN_1000_63f0(param_2,param_3);
  FUN_1000_6364();
  *(undefined1 *)0x41ba = 0;
  return;
}



/* 1000:6576 ReadBufferedWordLE
Calls ReadBufferedByte twice and combines first byte as low8bits, second as high8bits. */

// Calls ReadBufferedByte twice and combines first byte as low8bits, second as high8bits.

undefined2 __cdecl16near ReadBufferedWordLE(void)

{
  undefined1 uVar1;
  undefined1 uVar2;
  
  uVar1 = ReadBufferedByte();
  uVar2 = ReadBufferedByte();
  return CONCAT11(uVar2,uVar1);
}



/* 1000:6490 ReadBufferedByte
Reads current buffered byte from DS:41b0 then advances/refills using6326. Current return type is broader than meaningful low8bits. */

// Reads current buffered byte from DS:41b0 then advances/refills using6326. Current return type is
// broader than meaningful low8bits.

undefined2 __cdecl16near ReadBufferedByte(void)

{
  undefined2 uVar1;
  undefined2 unaff_DS;
  
  uVar1 = *(undefined2 *)0x41b0;
  FUN_1000_6326();
  return uVar1;
}



/* 1000:64ab ReadBufferedBitMSB
Returns highest bit of current byte, shifts left, decrements remaining count DS:41ae and loads next byte when count reaches0. */

// Returns highest bit of current byte, shifts left, decrements remaining count DS:41ae and loads
// next byte when count reaches0.

bool __cdecl16near ReadBufferedBitMSB(void)

{
  int *piVar1;
  undefined1 *puVar2;
  uint uVar3;
  undefined2 unaff_DS;
  
  uVar3 = (uint)*(byte *)0x41b0 << 1;
  *(byte *)0x41b0 = (byte)uVar3;
  piVar1 = (int *)0x41ae;
  *piVar1 = *piVar1 + -1;
  if (*piVar1 == 0) {
    *(undefined2 *)0x41ae = 8;
    puVar2 = (undefined1 *)*(undefined2 *)0x41b6;
    *(int *)0x41b6 = *(int *)0x41b6 + 1;
    if ((undefined1 *)*(undefined2 *)0x41b4 == puVar2) {
      FUN_1000_6350();
    }
    else {
      *(undefined1 *)0x41b0 = *puVar2;
    }
  }
  return (uVar3 & 0x100) != 0;
}



/* 1000:64ff ReadBufferedBitsMSB
Consumes requested number of MSB-first bits, accumulates result in AX. Current decompiler incorrectly infers void return; register semantics verified in raw instructions. Do not treat current prototype as recovered ABI. */

// Consumes requested number of MSB-first bits, accumulates result in AX. Current decompiler
// incorrectly infers void return; register semantics verified in raw instructions. Do not treat
// current prototype as recovered ABI.

void __cdecl16near ReadBufferedBitsMSB(int param_1)

{
  int *piVar1;
  undefined1 *puVar2;
  uint uVar3;
  uint uVar4;
  undefined2 unaff_DS;
  
  uVar3 = 0;
  while (param_1 = param_1 + -1, -1 < param_1) {
    uVar4 = (uint)*(byte *)0x41b0 << 1;
    *(byte *)0x41b0 = (byte)uVar4;
    uVar4 = (uint)((uVar4 & 0x100) != 0);
    piVar1 = (int *)0x41ae;
    *piVar1 = *piVar1 + -1;
    if (*piVar1 == 0) {
      *(undefined2 *)0x41ae = 8;
      puVar2 = (undefined1 *)*(undefined2 *)0x41b6;
      *(int *)0x41b6 = *(int *)0x41b6 + 1;
      if ((undefined1 *)*(undefined2 *)0x41b4 == puVar2) {
        FUN_1000_6350(param_1,uVar4,uVar3);
      }
      else {
        *(undefined1 *)0x41b0 = *puVar2;
      }
    }
    uVar3 = uVar3 | uVar4 << ((byte)param_1 & 0x1f);
  }
  return;
}



/* 1000:66e6 DecodeLzsBlock
Shared decoder for .LZS resources. Raw stack ABI: far destination at BP+4, uint16 output length at BP+8. Reads3 control bytes and patches instruction immediates at CS:6729,671f,674c and6751 (self-modifying decoder). Selects literal bytes or overlapping backreferences using MSB-first bit input; ends at output bound and aligns input. Label is based on resource filenames and algorithm shape; no exact external LZ variant or full decoder replay has been verified. Ghidra parameters shown in pseudocode are unreliable. */

// Shared decoder for .LZS resources. Raw stack ABI: far destination at BP+4, uint16 output length
// at BP+8. Reads3 control bytes and patches instruction immediates at CS:6729,671f,674c and6751
// (self-modifying decoder). Selects literal bytes or overlapping backreferences using MSB-first bit
// input; ends at output bound and aligns input. Label is based on resource filenames and algorithm
// shape; no exact external LZ variant or full decoder replay has been verified. Ghidra parameters
// shown in pseudocode are unreliable.

void __cdecl16near DecodeLzsBlock(undefined1 *param_1,int param_2)

{
  undefined1 *puVar1;
  undefined1 *puVar2;
  undefined1 uVar3;
  int iVar4;
  uint uVar5;
  undefined1 *puVar6;
  undefined1 *puVar7;
  undefined1 *puVar8;
  undefined2 uVar9;
  
  uVar9 = (undefined2)((ulong)param_1 >> 0x10);
  puVar7 = (undefined1 *)param_1;
  puVar1 = puVar7 + param_2;
  uRam00016729 = ReadBufferedByte();
                    // WARNING: Read-only address (ram,0x00016729) is written
  bRam0001671f = ReadBufferedByte();
                    // WARNING: Read-only address (ram,0x0001671f) is written
  iRam00016751 = 1 << (bRam0001671f & 0x1f);
                    // WARNING: Read-only address (ram,0x00016751) is written
  uRam0001674c = ReadBufferedByte();
                    // WARNING: Read-only address (ram,0x0001674c) is written
  while (puVar7 < puVar1) {
    iVar4 = ReadBufferedBitMSB();
    if (iVar4 == 0) {
      iVar4 = ReadBufferedBitsMSB(0);
LAB_1000_6723:
      puVar6 = puVar7 + (-2 - iVar4);
      iVar4 = ReadBufferedBitsMSB(0);
      uVar5 = iVar4 + 1;
      if ((uint)((int)puVar1 - (int)puVar7) <= uVar5) break;
      do {
        puVar8 = puVar7;
        puVar2 = puVar6;
        puVar6 = puVar6 + 1;
        *puVar8 = *puVar2;
        uVar5 = uVar5 - 1;
        puVar7 = puVar8 + 1;
      } while (uVar5 != 0);
      puVar7 = puVar8 + 2;
      puVar8[1] = *puVar6;
    }
    else {
      iVar4 = ReadBufferedBitMSB();
      if (iVar4 == 0) {
        iVar4 = ReadBufferedBitsMSB(0);
        iVar4 = iVar4 + -0xf10;
        goto LAB_1000_6723;
      }
      uVar3 = ReadBufferedBitsMSB(8);
      puVar2 = puVar7;
      puVar7 = puVar7 + 1;
      *puVar2 = uVar3;
    }
  }
  AlignBufferedInputToByte();
  return;
}



/* 1000:6679 AlignBufferedInputToByte
If remaining bit count is not8, consumes that count through ReadBufferedBitsMSB. Used after decoded blocks. */

// If remaining bit count is not8, consumes that count through ReadBufferedBitsMSB. Used after
// decoded blocks.

void __cdecl16near AlignBufferedInputToByte(void)

{
  undefined2 unaff_DS;
  
  if (*(int *)0x41ae != 8) {
    ReadBufferedBitsMSB(*(undefined2 *)0x41ae);
  }
  return;
}


