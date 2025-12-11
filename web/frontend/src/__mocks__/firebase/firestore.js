const mockFn = () => {};
mockFn.mockReturnValue = () => mockFn;
mockFn.mockImplementation = () => mockFn;

export const getFirestore = () => ({});
export const collection = () => ({});
export const doc = () => ({});
export const query = () => ({});
export const where = () => ({});
export const orderBy = () => ({});
export const limit = () => ({});
export const startAfter = () => ({});
export const endBefore = () => ({});
export const onSnapshot = () => () => {};
export const getDocs = () => Promise.resolve({ docs: [] });
export const getDoc = () => Promise.resolve({ exists: () => false });
export const setDoc = () => Promise.resolve();
export const updateDoc = () => Promise.resolve();
export const deleteDoc = () => Promise.resolve();
export const serverTimestamp = () => ({ toDate: () => new Date() });
export const Timestamp = {
  now: () => ({ toDate: () => new Date() }),
  fromDate: (date) => ({ toDate: () => date }),
};
