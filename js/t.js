// t.js - 真實公司薪資比較資料
// 從工作.csv提取的真實數據
window.companySalaries = {
  labels: ["Google", "台積電", "廣達", "鴻海", "IBM", "日月光"],
  datasets: [{
    label: "平均月薪資 (千元)",
    data: [69.85714285714286, 18.265, 60.0, 40.0, 300.0, 4.0],
    fill: true,
    backgroundColor: "rgba(106, 90, 205, 0.2)",
    borderColor: "rgba(106, 90, 205, 1)",
    pointBackgroundColor: "rgba(106, 90, 205, 1)",
    pointBorderColor: "#fff",
    pointHoverBackgroundColor: "#fff",
    pointHoverBorderColor: "rgba(106, 90, 205, 1)"
  }]
};

// 詳細薪資數據
window.salaryDetails = [
  {
    "company": "Google",
    "avg_salary": 69,
    "min_salary": 9,
    "max_salary": 200,
    "count": 7
  },
  {
    "company": "台積電",
    "avg_salary": 18,
    "min_salary": 5,
    "max_salary": 40,
    "count": 6
  },
  {
    "company": "廣達",
    "avg_salary": 60,
    "min_salary": 60,
    "max_salary": 60,
    "count": 2
  },
  {
    "company": "鴻海",
    "avg_salary": 40,
    "min_salary": 40,
    "max_salary": 40,
    "count": 2
  },
  {
    "company": "IBM",
    "avg_salary": 300,
    "min_salary": 300,
    "max_salary": 300,
    "count": 1
  },
  {
    "company": "日月光",
    "avg_salary": 4,
    "min_salary": 4,
    "max_salary": 4,
    "count": 1
  }
];

// 數據來源統計
window.salaryStats = {
  totalCompanies: 6,
  totalDataPoints: 19,
  averageSalary: 82,
  highestSalary: 300,
  lowestSalary: 4
};
