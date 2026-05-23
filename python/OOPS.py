
class Student:
    name=input("enter name:")
    roll_no=int(input("enter roll no:"))
    cgpa=float(input("enter cgpa:"))
    remark=input("any remarks?:")
s1=Student()
def show(self,n):
    self.name=n
    print("details after changing name:")
    print(self.name)
    print(self.roll_no)
    print(self.cgpa)
    print(self.remark)
name=input("enter what name u want to keep:")
show(s1,name)

