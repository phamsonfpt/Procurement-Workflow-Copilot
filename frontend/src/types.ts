export type Message = {
  id: string;
  sender: 'user' | 'Researcher' | 'Reviewer' | 'System' | 'Error';
  content: string;
  timestamp: Date;
};

export type AgentStatus = 'idle' | 'researching' | 'reviewing' | 'error';
export type Role = 'Requester' | 'Line Manager' | 'Department Head' | 'CFO' | 'Ops' | 'IT Admin';

export type UserProfile = {
  email: string;
  role: Role;
  name: string;
  department: string;
};

// Simulated Active Directory with standard corporate ratio
export const DIRECTORY: Record<string, UserProfile> = {
  // Requesters (Employees)
  'emp1@acme.corp': { email: 'emp1@acme.corp', role: 'Requester', name: 'Alice Nguyen', department: 'Engineering' },
  'emp2@acme.corp': { email: 'emp2@acme.corp', role: 'Requester', name: 'Bob Tran', department: 'Engineering' },
  'emp3@acme.corp': { email: 'emp3@acme.corp', role: 'Requester', name: 'Charlie Le', department: 'Marketing' },
  'emp4@acme.corp': { email: 'emp4@acme.corp', role: 'Requester', name: 'David Pham', department: 'Marketing' },
  'emp5@acme.corp': { email: 'emp5@acme.corp', role: 'Requester', name: 'Eva Vu', department: 'HR' },
  'emp6@acme.corp': { email: 'emp6@acme.corp', role: 'Requester', name: 'Frank Hoang', department: 'Sales' },
  'emp7@acme.corp': { email: 'emp7@acme.corp', role: 'Requester', name: 'Grace Bui', department: 'Sales' },
  'emp8@acme.corp': { email: 'emp8@acme.corp', role: 'Requester', name: 'Henry Do', department: 'Finance' },
  'emp9@acme.corp': { email: 'emp9@acme.corp', role: 'Requester', name: 'Ivy Dang', department: 'Engineering' },
  'emp10@acme.corp': { email: 'emp10@acme.corp', role: 'Requester', name: 'Jack Ly', department: 'IT' },

  // Line Managers
  'manager_eng@acme.corp': { email: 'manager_eng@acme.corp', role: 'Line Manager', name: 'Sarah Smith', department: 'Engineering' },
  'manager_mkt@acme.corp': { email: 'manager_mkt@acme.corp', role: 'Line Manager', name: 'Tom Hardy', department: 'Marketing' },
  'manager_sales@acme.corp': { email: 'manager_sales@acme.corp', role: 'Line Manager', name: 'Emma Watson', department: 'Sales' },

  // Department Heads
  'head_tech@acme.corp': { email: 'head_tech@acme.corp', role: 'Department Head', name: 'Mike Johnson', department: 'Engineering' },
  'head_biz@acme.corp': { email: 'head_biz@acme.corp', role: 'Department Head', name: 'Rachel Green', department: 'Business' },

  // C-Level
  'cfo@acme.corp': { email: 'cfo@acme.corp', role: 'CFO', name: 'Emily Davis', department: 'Executive' },

  // Procurement Operations
  'ops1@acme.corp': { email: 'ops1@acme.corp', role: 'Ops', name: 'Anna Lee', department: 'Operations' },
  'ops2@acme.corp': { email: 'ops2@acme.corp', role: 'Ops', name: 'Peter Parker', department: 'Operations' },

  // IT Admin
  'admin@acme.corp': { email: 'admin@acme.corp', role: 'IT Admin', name: 'Tom Wilson', department: 'IT' }
};

export type ThreadMeta = {
  thread_id: string;
  requester_email: string;
  title: string;
  total_cost: number;
  status: string;
  required_role: string;
  updated_at: string;
};
