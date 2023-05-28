import requests
import streamlit as st
from streamlit_lottie import st_lottie

st.set_page_config(page_title="My Webpage", page_icon=":open_book:", layout="wide")


def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()


# Load Assist
lottie_coding = load_lottieurl("https://assets6.lottiefiles.com/private_files/lf30_cldvedro.json")

# ----Head---
with st.container():
    st.subheader("Hi, I am Weilin :wave:")
    st.title("A data student")
    st.write("i am testing on this project")

with st.container():
    st.write("---")
    left_column, right_column = st.columns(2)
    with left_column:
        st.header("做筆記的原則")
        st.write("##")
        st.write(
            """
            - 原則一：寫得多不如寫得巧
            正如上面所說，總是一味的抄寫，是無法將上課所教的內容內化成自己的知識的，在之後的複習反而還需要花更多時間來思考當初抄的內容。比起狂抄黑板、課本上的文字寫到手痠，不如將這些大段的文字重點濃縮成最重要、一看到就會記起來的精華，筆記的多與少只是其次，只要筆記的內容真的有用、自己能看得懂就好。
            
            - 原則二：留白的重要
            在寫筆記的時候不可以追求把每一行都寫到滿，學會適當的留白是很重要的，留白可以增加我們筆記的擴充性，因為在寫完筆記之後可能會需要再加上一些新增的重點、時事，或者想把錯很多次的題目特別記上去提醒自己不要再犯，這時候寫在留白處就是很好的選擇。
            
            - 原則三：做好索引
            因為在做好一本筆記之後，裡面的內容一定會非常豐富，並不是那麼容易就可以找到自己想看的內容。如果想要快速的找到特定單元，那麼就一定要將索引做好！例如在每個單元旁貼上便利貼標籤就是一個很好的方法，不需要把整本筆記本都翻完，就可以找到自己想看的內容。
            """
        )
        st.write("[source link>](https://tw.amazingtalker.com/blog/zh-tw/k12/70276/)")
    with right_column:
        st_lottie(lottie_coding, height=300, key="noting")

# --- Projects ---


