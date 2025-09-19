resource "aws_route53_record" "api" {
  zone_id = "Z123456789ABC"  # Get this from AWS Console → Route53 → cab432.com
  name    = "n11957948.cab432.com"
  type    = "CNAME"
  ttl     = "300"
  records = [aws_instance.your_ec2_instance.public_dns]  # Your EC2 instance
}

output "domain_name" {
  value = aws_route53_record.api.fqdn
}