import razorpay

RAZORPAY_KEY_ID = "rzp_test_20tkfyOZteuJyu"
RAZORPAY_KEY_SECRET = "bMrRXLvsfNu2ij51fcn3UZPu"

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
