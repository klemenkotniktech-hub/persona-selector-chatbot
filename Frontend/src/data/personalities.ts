export interface Personality {
  id: string;
  name: string;
  description: string;
  imagePath: string;
}

export const personalities: Personality[] = [
  {
    id: "1",
    name: "Accountant",
    description: "A detail-oriented professional who can help with financial matters and tax advice.",
    imagePath: "/assets/personalities/Accountant.jpg"
  },
  {
    id: "2",
    name: "Childhood Friend",
    description: "A warm and familiar presence who knows you well and offers casual, friendly conversation.",
    imagePath: "/assets/personalities/Childhood Friend.jpg"
  },
  {
    id: "3",
    name: "Clinical Psychologist",
    description: "A trained mental health professional who offers thoughtful insights and supportive guidance.",
    imagePath: "/assets/personalities/Clinical Psychologist.jpg"
  },
  {
    id: "4",
    name: "Doctor",
    description: "A medical professional who can provide general health information and wellness advice.",
    imagePath: "/assets/personalities/Doctor.jpg"
  },
  {
    id: "5",
    name: "Engineer",
    description: "A technical expert who excels at problem-solving and can explain complex concepts clearly.",
    imagePath: "/assets/personalities/Engineer.jpg"
  },
  {
    id: "6",
    name: "Lawyer",
    description: "A legal professional who can provide general information about legal concepts and processes.",
    imagePath: "/assets/personalities/Lawyer.jpg"
  }
];