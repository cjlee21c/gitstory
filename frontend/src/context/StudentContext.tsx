import { createContext, useContext, useState } from "react";

interface StudentContextValue {
  studentId: string;
  setStudentId: (id: string) => void;
}

const StudentContext = createContext<StudentContextValue>({
  studentId: "",
  setStudentId: () => {},
});

export function StudentProvider({ children }: { children: React.ReactNode }) {
  const [studentId, setStudentId] = useState(() => {
    return localStorage.getItem("studentId") ?? "";
  });

  function handleSet(id: string) {
    localStorage.setItem("studentId", id);
    setStudentId(id);
  }

  return (
    <StudentContext.Provider value={{ studentId, setStudentId: handleSet }}>
      {children}
    </StudentContext.Provider>
  );
}

export function useStudent() {
  return useContext(StudentContext);
}
