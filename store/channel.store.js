// status.js
export const statusList = [];

export function addStatus(obj) {
    statusList.unshift(obj);
}

export function updateStatus(id, updates) {
    const idx = statusList.findIndex(s => s.id === id);
    if (idx >= 0) statusList[idx] = { ...statusList[idx], ...updates };
}

export function getStatus() {
    return statusList;
}
