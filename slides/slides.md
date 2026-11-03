---
theme: seriph
title: Vibe-code 101
info: |
  ## Vibe-code 101
  From Zero to Hero in 30 days
class: text-center
drawings:
  persist: false
transition: slide-left
comark: true
---

# Vibe-code 101

From Zero to Hero in 30 days

---
layout: default
---

# Tác nhân AI (AI Agent)

Tổng quan

- Mô hình ngôn ngữ lớn (LLM)
- Hội thoại & phiên làm việc
- Kho tri thức
- Bộ nhớ
- Kĩ năng & công cụ

---
layout: default
---

# Mô hình ngôn ngữ lớn

<video src="./media/LLMInAction.mp4" class="mx-auto mt-4 h-96 rounded" controls muted loop autoplay></video>

---

# Mô hình ngôn ngữ lớn: Các thông số cơ bản

<div class="grid gap-6 mt-8">

<div>

## 01 · Input

Là phần văn bản gửi vào mô hình. Văn bản được tách thành token, khoảng 1 token ≈ 4 ký tự tiếng Anh. Tiếng Việt thường tốn nhiều token hơn trên cùng một nội dung.

</div>

<div>

## 02 · Output

Là phần mô hình sinh ra (câu trả lời, mã, văn bản). Chi phí cũng tính theo USD trên 1 triệu token. Thường đắt hơn input khoảng 3–5 lần vì mỗi token phải sinh tuần tự.

</div>

<div>

## 03 · Context window (cửa sổ ngữ cảnh)

Là tổng số token mô hình xử lý được trong một lượt, gồm cả input và output. Nếu vượt quá giới hạn, nội dung cũ bị cắt hoặc yêu cầu bị từ chối.

</div>

</div>

---

# Mô hình ngôn ngữ lớn: Các chế độ hoạt động

<div class="grid gap-6 mt-8">

<div>

## 01 · Chat

Hội thoại thông thường, trả lời trực tiếp.

Nhanh, rẻ, phù hợp hỏi đáp, viết nội dung, dịch.

</div>

<div>

## 02 · Thinking (suy luận)

Mô hình "suy nghĩ" từng bước trước khi trả lời.

Chính xác hơn với toán, lập trình, logic phức tạp. Chậm hơn và tốn thêm token suy luận.

</div>

<div>

## 03 · Vision (thị giác)

Hiểu đầu vào là hình ảnh, ảnh chụp màn hình, PDF, biểu đồ.

Đọc hóa đơn, phân tích biểu đồ, mô tả ảnh. Ảnh được quy đổi thành token nên cũng tính vào input.

</div>

</div>

---

# Mô hình ngôn ngữ lớn: Cách xây dựng cửa sổ ngữ cảnh

<div class="grid grid-cols-2 gap-8 mt-8">

<div>

## 01 · Liên quan

Chỉ chứa thông tin phục vụ trực tiếp cho tác vụ hiện tại. Nội dung thừa gây nhiễu và làm mô hình lạc hướng.

</div>

<div>

## 02 · Đầy đủ

Có đủ dữ kiện, ví dụ và ràng buộc cần thiết. Thiếu thông tin khiến mô hình phải đoán hoặc bịa.

</div>

<div>

## 03 · Gọn & có cấu trúc

Tiết kiệm token, chia mục rõ ràng, đặt thông tin quan trọng ở đầu hoặc cuối. Tránh vượt giới hạn context window.

</div>

<div>

## 04 · Chính xác & nhất quán

Thông tin được cập nhật, không mâu thuẫn giữa các nguồn (hội thoại, tri thức, bộ nhớ).

</div>

</div>

---

# Ví dụ: Xây dựng cửa sổ ngữ cảnh từng bước

<div class="grid grid-cols-[1fr_16rem] gap-8 mt-6 text-left">

<div class="flex flex-col justify-end gap-3 border-2 border-gray-400 rounded-lg p-3 h-[26rem] text-xs">

<div v-click="4" class="rounded p-3 bg-green-100 text-green-900 text-xs">
<b>05 · Định dạng</b> — Web app responsive, truy cập được trên desktop và mobile.
</div>

<div v-click="3" class="rounded p-3 bg-purple-100 text-purple-900 text-xs">
<b>04 · Giao diện (tóm tắt)</b> — Tối giản: màn hình Tổng quan thể hiện thu chi, danh sách giao dịch, nút "+" thêm nhanh, lọc theo tháng và danh mục, có chức năng tạo báo cáo.
</div>

<div v-click="2" class="rounded p-3 bg-orange-100 text-orange-900 text-xs">
<b>03 · Ví dụ</b> — Đầu vào → bản ghi mong muốn:
<ul class="text-xs mt-1">
<li>"Cà phê 45k sáng nay" → Chi · 45.000 ₫ · Ăn uống</li>
<li>"Nhận lương tháng 10: 15tr" → Thu · 15.000.000 ₫ · Lương</li>
<li>Ảnh hóa đơn siêu thị → Chi · tổng tiền trên hóa đơn · Đi chợ</li>
</ul>
</div>

<div v-click="1" class="rounded p-3 bg-amber-100 text-amber-900 text-xs">
<b>02 · Bối cảnh (tóm tắt)</b> — Người dùng cá nhân ghi thu chi hằng ngày bằng tiền mặt và hóa đơn tay, tôi muốn tạo 1 app để người dùng thuận tiện nhập, upload hóa đơn để theo dõi thu chi.
</div>

<div class="rounded p-3 bg-blue-100 text-blue-900 text-xs">
<b>01 · Yêu cầu</b> — Help me create an app to track income and expense
</div>

</div>

<div class="flex flex-col gap-3">

<div class="text-sm">Mức độ đầy đủ của ngữ cảnh</div>

<div class="h-4 w-full rounded bg-gray-200">
<div class="h-4 rounded bg-blue-500 transition-all duration-500" :class="$clicks >= 4 ? 'w-full' : $clicks >= 3 ? 'w-5/6' : $clicks >= 2 ? 'w-2/3' : $clicks >= 1 ? 'w-1/2' : 'w-1/4'"></div>
</div>

<div class="text-sm opacity-70">
<span v-if="$clicks === 0">Chỉ có yêu cầu: mô hình phải tự đoán mọi thứ.</span>
<span v-else-if="$clicks === 1">Thêm bối cảnh: hiểu người dùng và mục tiêu.</span>
<span v-else-if="$clicks === 2">Thêm ví dụ: biết đầu ra cần đúng dạng nào.</span>
<span v-else-if="$clicks === 3">Thêm giao diện: biết app trông như thế nào.</span>
<span v-else>Thêm định dạng: kết quả đúng nền tảng cần dùng.</span>
</div>

</div>

</div>

---
layout: section
---

# Tác nhân AI

---

# Tác nhân AI là gì?

Một hệ thống dùng mô hình ngôn ngữ lớn làm "bộ não" để hiểu mục tiêu, tự lập kế hoạch, dùng công cụ và thực hiện nhiều bước cho đến khi hoàn thành nhiệm vụ.

<div class="grid grid-cols-2 gap-6 mt-6 text-left text-sm">

<div>

#### 01 · Mô hình ngôn ngữ lớn (LLM)

Bộ não: hiểu yêu cầu, suy luận và quyết định bước tiếp theo.

</div>

<div>

#### 02 · Hội thoại & phiên làm việc

Lưu diễn biến trao đổi hiện tại để agent giữ mạch công việc.

</div>

<div>

#### 03 · Kho tri thức

Tài liệu, dữ liệu, wiki mà agent tra cứu để trả lời chính xác theo bối cảnh của bạn.

</div>

<div>

#### 04 · Bộ nhớ

Ghi nhớ dữ liệu, quy ước và kinh nghiệm qua nhiều phiên làm việc.

</div>

<div class="col-span-2">

#### 05 · Kĩ năng & công cụ

Quy trình đóng gói sẵn và khả năng hành động: đọc/ghi tệp, chạy lệnh, truy vấn cơ sở dữ liệu, duyệt web.

</div>

</div>

---

# Tổng quan về Tác nhân AI

<video src="./media/AgentLifecycle.mp4" class="mx-auto mt-4 h-96 rounded" controls muted loop autoplay></video>

---

# Quy trình làm việc với AI Agent: 4 bước

<div class="grid grid-cols-2 gap-6 mt-6 text-left text-sm">

<div>

#### 01 · Hình thành ý tưởng

Trao đổi với agent để làm rõ mục tiêu, phạm vi và ràng buộc. Agent đặt câu hỏi, bạn trả lời cho đến khi ý tưởng đủ rõ.

</div>

<div>

#### 02 · Tài liệu hóa

Ghi ý tưởng thành trang wiki: mô tả, quyết định và cấu trúc dữ liệu. Đây là kho tri thức để agent và bạn quay lại tra cứu.

</div>

<div>

#### 03 · Triển khai

Agent viết code, tạo skill và cơ sở dữ liệu dựa trên tài liệu. Quy trình lặp lại được đóng gói thành skill để tái sử dụng.

</div>

<div>

#### 04 · Kiểm thử

Chạy thử các tình huống thực tế, đối chiếu với kỳ vọng. Phát hiện lỗi thì sửa, đạt yêu cầu thì sang tính năng tiếp theo.

</div>

<div class="col-span-2">

#### Lặp lại

Mỗi vòng thêm một tính năng và để lại thêm tài liệu, code, skill, nên sau mỗi vòng lặp thì ứng dụng sẽ ngày càng hoàn thiện hơn.

</div>

</div>

---

# Quy trình làm việc với AI Agent

<video src="./media/AIWorkflowLoop.mp4" class="mx-auto mt-4 h-96 rounded" controls muted loop autoplay></video>

---
layout: default
---

# Các cấp độ sử dụng AI

<div class="grid grid-cols-2 gap-8 mt-4 text-left items-center">

<div class="flex flex-col gap-4 text-sm">

<div>

#### 01 · Sử dụng ChatGPT
Hỏi đáp trực tiếp trong khung chat. Bạn tự sao chép kết quả đi dùng, AI chỉ trả lời và không tự hành động.

</div>

<div>

#### 02 · Làm việc với AI Agent
Giao việc cho agent. Agent tự đọc tệp, dùng công cụ và thực hiện nhiều bước, bạn theo dõi và duyệt kết quả.

</div>

<div>

#### 03 · Tự động hóa AI Agent
Đặt agent chạy theo quy trình có sẵn (kĩ năng, lịch chạy, sự kiện kích hoạt) mà không cần ra lệnh mỗi lần.

</div>

<div>

#### 04 · Quản lý đội ngũ AI Agent
Điều phối nhiều agent chuyên biệt cùng làm việc, mỗi agent một vai trò. Bạn đặt mục tiêu, phân công và kiểm soát chất lượng.

</div>

</div>

<img src="./media/ai_4level.jpg" class="mx-auto h-96 rounded" />

</div>

<style>
p {
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}
</style>