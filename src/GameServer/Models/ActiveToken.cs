using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace GameServer.Models
{
    public class ActiveToken
    {
        [Key]
        public int Id { get; set; }

        [Required]
        public required string Token { get; set; }

        [Required]
        public Guid AccountId { get; set; }

        [ForeignKey("AccountId")]
        public virtual Account Account { get; set; } = null!;

        public DateTime Expires { get; set; }
    }
}
