import sys
import os
from giving_solution import improve_problem_statement
from PyQt5.QtWidgets import QApplication,QMainWindow,QLabel,QLineEdit,QPushButton,QVBoxLayout,QWidget
from PyQt5.QtGui import QFont
class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Statement Correction")
       

        self.label =QLabel("Statement to correct :",self)
        self.label.setFont(QFont("Arial",20))
        
        self.layout=QVBoxLayout()
        self.layout.addWidget(self.label)

        self.textbox=QLineEdit(self)
        self.textbox.setStyleSheet("font-size : 20px; font-family:arial;")
        self.textbox.setPlaceholderText("statement")
        self.layout.addWidget(self.textbox)
        
        self.button= QPushButton("improve",self)
        self.button.setStyleSheet("font-size: 20px ;font-family:arial;")
        self.button.clicked.connect(self.improve)
        self.layout.addWidget(self.button)

        self.label2 =QLabel("Improved statement :",self)
        self.label2.setFont(QFont("Arial",20))
        self.layout.addWidget(self.label2)
        
        self.label3 =QLabel("",self)
        self.label3.setFont(QFont("Arial",10))
        
        self.label3.setWordWrap(True)

        self.layout.addWidget(self.label3)

        self.label4 =QLabel("solutions suggested :",self)
        self.label4.setFont(QFont("Arial",20))
        self.layout.addWidget(self.label4)
       
        self.label5=QLabel("",self)
       
        self.label5.setFont(QFont("Arial",10))
        self.label5.setWordWrap(True)
        self.layout.addWidget(self.label5)

        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

        

    def improve(self):
        text=self.textbox.text()
        result=improve_problem_statement(text)
        self.label3.setText(result["clear_problem"])
        self.label5.setText(result["solutions"])
        

       

def main():
    app=QApplication(sys.argv)
    window=MyWindow()
    window.show()
    sys.exit(app.exec_())
    
    



if __name__=="__main__":
    main()