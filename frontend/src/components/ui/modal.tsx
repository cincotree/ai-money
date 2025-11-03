import React from 'react';

const styles = {
    dialog: {
        position: 'fixed' as const,
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
    },
    dialogOverlay: {
        position: 'absolute' as const,
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
    },
    dialogContent: {
        position: 'relative' as const,
        backgroundColor: '#f9fafb',
        padding: '20px',
        borderRadius: '8px',
        boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
        zIndex: 1001,
    },
    dialogContentInner: {
        padding: '10px',
    },
    dialogHeader: {
        marginBottom: '10px',
    },
    dialogTitle: {
        margin: 0,
        fontSize: '1.5em',
        color: '#1f2937',
    },
    dialogFooter: {
        marginTop: '10px',
        textAlign: 'right' as const,
    },
};

interface DialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    children: React.ReactNode;
}

interface DialogContentProps {
    children: React.ReactNode;
}

export const Modal = ({ open, onOpenChange, children }: DialogProps) => {
    if (!open) return null;

    return (
        <div style={styles.dialog}>
            <div style={styles.dialogOverlay} onClick={() => onOpenChange(false)} />
            <div style={styles.dialogContent}>{children}</div>
        </div>
    );
};

export const DialogContent = ({ children }: DialogContentProps) => (
    <div style={styles.dialogContentInner}>{children}</div>
);

export const DialogHeader = ({ children }: { children: React.ReactNode }) => (
    <div style={styles.dialogHeader}>{children}</div>
);

export const DialogTitle = ({ children }: { children: React.ReactNode }) => (
    <h2 style={styles.dialogTitle}>{children}</h2>
);

export const DialogFooter = ({ children }: { children: React.ReactNode }) => (
    <div style={styles.dialogFooter}>{children}</div>
);
