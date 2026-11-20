// drivers/wormdrv/wormdrv.c
// WormDrv — قالب گرافیکي للقراءة/الكتابة بالذاكرة من النواة (educational template).
// يوفر IOCTL: IOCTL_WORM_READ / IOCTL_WORM_WRITE عبر MmCopyVirtualMemory.
// البناء: يحتاج WDK + VS (انظر build.ps1) والاختبار يتقدم تحت test sign / secure kernel off.
// عدل بالأمان: driver يشروط المسار (قارئ حجم mm) ولا يمس عمليات خاصة (System, Critical).
#include <ntifs.h>
#include <ntstrsafe.h>

#define WORMDEV_DEVICE_NAME L"\\Device\\WormDrv"
#define WORMDEV_SYMBOLIC    L"\\??\\WormDrv"

#define IOCTL_BASE   0x8000
#define IOCTL_WORM_OPEN   CTL_CODE(FILE_DEVICE_UNKNOWN, IOCTL_BASE+1, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_WORM_READ   CTL_CODE(FILE_DEVICE_UNKNOWN, IOCTL_BASE+2, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_WORM_WRITE  CTL_CODE(FILE_DEVICE_UNKNOWN, IOCTL_BASE+3, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_WORM_CLOSE  CTL_CODE(FILE_DEVICE_UNKNOWN, IOCTL_BASE+4, METHOD_BUFFERED, FILE_ANY_ACCESS)

typedef struct _WORM_TARGET {
    HANDLE pid;      // target process id
    ULONGLONG addr;  // virtual address in target
    ULONGLONG size;  // bytes to copy
} WORM_TARGET, *PWORM_TARGET;

static PEPROCESS         g_TargetProc = NULL;
static HANDLE            g_TargetPid  = 0;
static UNICODE_STRING    g_SymLink;

// ---------------------------------------------------------------------------
// Resolve target process (protected processes excluded).
// ---------------------------------------------------------------------------
static NTSTATUS WormOpenTarget(HANDLE pid)
{
    PEPROCESS proc = NULL;
    NTSTATUS st = PsLookupProcessByProcessId(pid, &proc);
    if (!NT_SUCCESS(st)) return st;
    // PCW protection filter: skip critical processes
    if (PsIsProtectedProcess(proc)) {
        ObDereferenceObject(proc);
        return STATUS_ACCESS_DENIED;
    }
    if (g_TargetProc) ObDereferenceObject(g_TargetProc);
    g_TargetProc = proc;
    g_TargetPid  = pid;
    return STATUS_SUCCESS;
}

// ---------------------------------------------------------------------------
// Read / Write via MmCopyVirtualMemory ( коль 0-Zêter instruct).
// ---------------------------------------------------------------------------
static NTSTATUS WormCopy(ULONGLONG target_addr, ULONGLONG size,
                         BOOLEAN write, PVOID user_buf, PSIZE_T xferred)
{
    NTSTATUS st;
    SIZE_T  bytes = 0;
    PEPROCESS cur = PsGetCurrentProcess();
    if (!g_TargetProc) return STATUS_INVALID_HANDLE;
    if (size > 0x8000000) return STATUS_INVALID_PARAMETER;   // 128MB بحد
    KAPC_STATE state;
    KeStackAttachProcess(g_TargetProc, &state);
    __try {
        st = MmCopyVirtualMemory(write ? cur            : g_TargetProc,
                                  write ? user_buf      : (PVOID)(ULONG_PTR)target_addr,
                                  write ? g_TargetProc  : cur,
                                  write ? (PVOID)(ULONG_PTR)target_addr : user_buf,
                                  size, UserMode, &bytes);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        st = GetExceptionCode();
    }
    KeUnstackDetachProcess(&state);
    if (xferred) *xferred = bytes;
    return st;
}

// ---------------------------------------------------------------------------
// IRP_MJ_DEVICE_CONTROL
// ---------------------------------------------------------------------------
static NTSTATUS WormDeviceControl(PDEVICE_OBJECT dev, PIRP irp)
{
    UNREFERENCED_PARAMETER(dev);
    PIO_STACK_LOCATION stack = IoGetCurrentIrpStackLocation(irp);
    NTSTATUS st = STATUS_SUCCESS;
    ULONG  out_len = stack->Parameters.DeviceIoControl.OutputBufferLength;
    PVOID  buf     = irp->AssociatedIrp.SystemBuffer;
    PCHAR  out     = (PCHAR)buf;

    switch (stack->Parameters.DeviceIoControl.IoControlCode) {
    case IOCTL_WORM_OPEN: {
        PWORM_TARGET t = (PWORM_TARGET)buf;
        st = WormOpenTarget(t->pid);
        break;
    }
    case IOCTL_WORM_READ: {
        SIZE_T copied = 0;
        PWORM_TARGET t = (PWORM_TARGET)buf;
        st = WormCopy(t->addr, t->size, FALSE, buf, &copied);
        if (NT_SUCCESS(st) && out_len >= t->size)
            irp->IoStatus.Information = t->size;
        break;
    }
    case IOCTL_WORM_WRITE: {
        SIZE_T copied = 0;
        PWORM_TARGET t = (PWORM_TARGET)buf;
        st = WormCopy(t->addr, t->size, TRUE, (PVOID)((PCHAR)buf + 16), &copied);
        break;
    }
    case IOCTL_WORM_CLOSE:
        if (g_TargetProc) {
            ObDereferenceObject(g_TargetProc);
            g_TargetProc = NULL;
        }
        st = STATUS_SUCCESS;
        break;
    default:
        st = STATUS_INVALID_DEVICE_REQUEST;
    }

    irp->IoStatus.Status = st;
    IoCompleteRequest(irp, IO_NO_INCREMENT);
    return st;
}

// ---------------------------------------------------------------------------
// Dispatch stubs
// ---------------------------------------------------------------------------
static NTSTATUS WormCreateClose(PDEVICE_OBJECT dev, PIRP irp)
{
    UNREFERENCED_PARAMETER(dev);
    irp->IoStatus.Status = STATUS_SUCCESS;
    irp->IoStatus.Information = 0;
    IoCompleteRequest(irp, IO_NO_INCREMENT);
    return STATUS_SUCCESS;
}

static VOID WormUnload(PDRIVER_OBJECT drv)
{
    UNREFERENCED_PARAMETER(drv);
    if (g_TargetProc) ObDereferenceObject(g_TargetProc);
    RtlFreeUnicodeString(&g_SymLink);
    IoDeleteDevice(drv->DeviceObject);
}

// ---------------------------------------------------------------------------
// DriverEntry
// ---------------------------------------------------------------------------
extern "C" NTSTATUS DriverEntry(PDRIVER_OBJECT drv, PUNICODE_STRING reg)
{
    UNREFERENCED_PARAMETER(reg);
    NTSTATUS st;
    PDEVICE_OBJECT device = NULL;

    RtlInitUnicodeString(&g_SymLink, WORMDEV_SYMBOLIC);
    st = IoCreateDevice(drv, 0, NULL, FILE_DEVICE_UNKNOWN, 0, FALSE, &device);
    if (!NT_SUCCESS(st)) return st;

    st = IoCreateSymbolicLink(&g_SymLink, &g_SymLink);
    if (!NT_SUCCESS(st)) {
        IoDeleteDevice(device);
        return st;
    }

    drv->MajorFunction[IRP_MJ_CREATE]         = WormCreateClose;
    drv->MajorFunction[IRP_MJ_CLOSE]          = WormCreateClose;
    drv->MajorFunction[IRP_MJ_DEVICE_CONTROL] = WormDeviceControl;
    drv->DriverUnload = WormUnload;

    KdPrint(("WormDrv: driver loaded, symbolic: %wZ\n", &g_SymLink));
    return STATUS_SUCCESS;
}
