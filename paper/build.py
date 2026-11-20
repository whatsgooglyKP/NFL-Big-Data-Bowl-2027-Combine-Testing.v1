import pypandoc, re, subprocess
s=open('paper.md').read()
n=[0]
def f(m):
    n[0]+=1
    return f"![**Figure {n[0]}.** {m.group(1)}]("
s2=re.sub(r"!\[(?!\*\*Figure)(.*?)\]\(", f, s)
open('paper_build.md','w').write(s2)
base='Pinard_BDB2027_Read_the_Combine_Through_Body_Size'
pypandoc.convert_file('paper_build.md','html5',outputfile='paper.html',extra_args=['--standalone','--mathml','--css=paper.css','--embed-resources','--metadata','pagetitle=Read the Combine Through Body Size'])
pypandoc.convert_file('paper_build.md','docx',outputfile=base+'.docx')
subprocess.run(['google-chrome','--headless=new','--no-sandbox','--disable-gpu','--no-pdf-header-footer',f'--print-to-pdf={base}.pdf','paper.html'],stderr=subprocess.DEVNULL)
print('figs',n[0])
